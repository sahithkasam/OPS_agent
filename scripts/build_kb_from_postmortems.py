"""Build the RAG knowledge base from real public postmortems.

Source: Dan Luu's "A List of Post-mortems!" (github.com/danluu/post-mortems),
a curated collection of real production outage write-ups from companies such
as AWS, Google, Cloudflare, GitHub and Stripe. Each entry is a link to the
original postmortem plus a short summary.

Every entry is turned into the incident schema the RCA agent searches:

    id, company, source_url, section, category, summary, description,
    symptoms, logs_signature, root_cause, resolution, recommended_action,
    severity, duration

`category` is one of the simulator's incident types, so an injected incident
retrieves real postmortems of the same kind.

Two extraction modes:
  * LLM mode (GROQ_API_KEY / OPENAI_API_KEY / OLLAMA set): the LLM reads each
    summary and fills in the fields. Rule-based values are passed in as hints.
  * Rule-based mode (default when no key is configured, or with --no-llm):
    deterministic keyword rules. Fields the summary doesn't mention (often
    the resolution) are left empty instead of being invented.

LLM progress is saved after every entry (data/historical_incidents.progress.jsonl),
so an interrupted run resumes where it stopped: just run the command again.

Usage (from the project root):
    python scripts/build_kb_from_postmortems.py              # build (resumes if interrupted)
    python scripts/build_kb_from_postmortems.py --no-llm     # rules only
    python scripts/build_kb_from_postmortems.py --download   # use the latest upstream list
    python scripts/build_kb_from_postmortems.py --fresh      # discard saved LLM progress
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SOURCE_URL = "https://raw.githubusercontent.com/danluu/post-mortems/master/README.md"
# Pinned copy of the list, so rebuilds are reproducible even if upstream changes.
SOURCE_SNAPSHOT = ROOT / "data" / "raw" / "danluu_post-mortems_README.md"
OUT_PATH = ROOT / "data" / "historical_incidents.json"

# Must stay in sync with src/simulation/incident.py::IncidentType
CATEGORIES = [
    "bad_deploy", "dns_failure", "network_latency", "service_down",
    "database_lock", "ssl_expiry", "memory_leak", "high_cpu",
    "disk_usage_high", "process_crash",
]

# Action names line up with src/orchestration/policy_engine.py so the
# safety gate classifies them correctly.
DEFAULT_ACTION = {
    "bad_deploy": "Rollback Deployment",
    "dns_failure": "Rollback Deployment",
    "network_latency": "Reroute Traffic",
    "service_down": "Restart Service",
    "database_lock": "Failover Database",
    "ssl_expiry": "Renew Certificate",
    "memory_leak": "Restart Service",
    "high_cpu": "Scale Resources",
    "disk_usage_high": "Free Disk Space",
    "process_crash": "Restart Service",
}
ALLOWED_ACTIONS = sorted(set(DEFAULT_ACTION.values()) | {"Clear Cache", "Escalate to L3"})

# Ordered: the first category whose pattern matches wins. Specific failure
# modes come before generic ones ("a config change broke DNS" is a DNS
# incident for retrieval purposes).
CATEGORY_RULES = [
    ("ssl_expiry", r"\bcert(ificate)?s?\b|\btls\b|\bssl\b"),
    ("dns_failure", r"\bdns\b|\bresolver\b|\bnameserver|\bdomain name|\bservfail\b"),
    ("database_lock", r"\bdatabases?\b|\bdb\b|postgres|mysql|\bsql\b|mongo|replica|replication|\bschema\b|\bdeadlock|\block(s|ing)?\b|cassandra|etcd|zookeeper|redis"),
    ("disk_usage_high", r"\bdisks?\b|out of space|no space|disk space|\bstorage\b|filesystem|inode|\bebs\b"),
    ("memory_leak", r"\bmemory\b|\boom\b|out of memory|memory leak|leaking|\bheap\b|garbage collect"),
    ("network_latency", r"\bnetwork|\bbgp\b|\brouter|\bpacket|\blatency|partition|\bfib(er|re)\b|\blink\b|load balancer|\bswitch(es)?\b|backbone|\bcdn\b|congest"),
    ("high_cpu", r"\bcpu\b|overload|traffic spike|thundering herd|\bcapacity\b|\bload\b|exhaust|throttl|\bregex\b|backtrack"),
    ("bad_deploy", r"\bdeploy|\bconfig|\brollout|\brolled out|\brelease|\bpush(ed)?\b|\bchange\b|\btypo\b|\bmigration\b|\bupgrade"),
    ("process_crash", r"\bcrash|\bpanic|segfault|leap second|restart loop|\bbug\b|exception|\bhang|deadlock"),
]

# A single mention of DNS or a certificate is usually decisive; generic words
# like "change" or "load" are not.
CATEGORY_WEIGHT = {"ssl_expiry": 2.5, "dns_failure": 2.5, "memory_leak": 1.5, "disk_usage_high": 1.5}

SECTION_DEFAULT = {
    "Config Errors": "bad_deploy",
    "Hardware/Power Failures": "service_down",
    "Conflicts": "service_down",
    "Time": "process_crash",
    "Database": "database_lock",
}

SYMPTOM_RULES = [
    (r"\b5\d\d\b|\berrors?\b|failed|failures?", "elevated error rate"),
    (r"\blatency|slow|timeouts?|timed out", "high latency / timeouts"),
    (r"\bdown\b|outage|unavailable|offline|went down", "service unavailable"),
    (r"\bdns\b|servfail|resolution", "DNS resolution failures"),
    (r"\bcpu\b|overload", "CPU saturation"),
    (r"\bmemory\b|\boom\b", "memory exhaustion"),
    (r"\bdisk|no space|storage", "disk full / storage errors"),
    (r"cert|\btls\b|\bssl\b", "TLS handshake / certificate errors"),
    (r"databases?|\bdb\b|replica", "database errors"),
    (r"packet|\bbgp\b|route|network", "network packet loss / routing errors"),
    (r"crash|panic|restart", "process crashes / restarts"),
    (r"data loss|lost data|deleted", "data loss"),
]

CAUSE_WORDS = re.compile(r"\b(caus|due to|because|result|trigger|bug|misconfig|error|incorrect|wrong|typo|fail)", re.I)
FIX_WORDS = re.compile(r"\b(roll(ed|ing)? back|rollback|revert|restor|fixed|mitigated|restart|recovered|remediat|failover|failed over|manually|disabled|re-?enabl|patched|resolved)", re.I)
P1_WORDS = re.compile(r"\b(all|entire|global|globally|worldwide|whole|every|complete|total|systemwide|system-wide|major|massive|hours)\b", re.I)
P3_WORDS = re.compile(r"\b(some users|small (number|percentage|fraction)|minor|partial|a few|subset|briefly)\b", re.I)
DURATION_RE = re.compile(r"(~|about |around |over |almost |nearly )?(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?|days?)\b", re.I)
ENTRY_RE = re.compile(r"^\[([^\]]+)\]\(([^)\s]+)\)\.?\s*(.*)$")


def fetch_source(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    import requests
    resp = requests.get(SOURCE_URL, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_entries(markdown: str) -> list[dict]:
    """Parse '[Company](url). Summary...' lines, stopping before the
    non-incident sections at the end of the list."""
    entries, section = [], None
    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            if section.lower().startswith(("other lists", "analysis", "contributors")):
                break
            continue
        if section in (None, "Table of Contents"):
            continue
        m = ENTRY_RE.match(line)
        if not m:
            continue
        company, url, text = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        # Strip leftover markdown links inside the summary text.
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        if len(text) < 40 or is_security_incident(text):
            continue
        entries.append({"company": company, "source_url": url, "section": section, "description": text})
    return entries


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text)
    return [p.strip() for p in parts if p.strip()]


SECURITY_RE = re.compile(r"\b(attack(er|ers|s)?|breach|exfiltrat|compromis|hack(ed|ers?)?|malicious|threat actors?|phishing|ransomware|stolen|leaked|data leaks?|leak of|private information|personal data)\b", re.I)


def is_security_incident(text: str) -> bool:
    """Security breaches aren't operational incidents the agent can remediate."""
    return bool(SECURITY_RE.search(text))


def classify(text: str, section: str) -> str:
    """Score every category by its number of keyword hits; the section the
    entry was filed under counts as half a hit. Ties go to the more specific
    category (earlier in CATEGORY_RULES)."""
    low = text.lower()
    best, best_score = None, 0.0
    for cat, pattern in CATEGORY_RULES:
        score = len(re.findall(pattern, low)) * CATEGORY_WEIGHT.get(cat, 1.0)
        if SECTION_DEFAULT.get(section) == cat:
            score += 0.5
        if score > best_score:
            best, best_score = cat, score
    return best or SECTION_DEFAULT.get(section, "service_down")


def rule_extract(entry: dict) -> dict:
    text = entry["description"]
    sents = sentences(text)
    category = classify(text, entry["section"])

    cause = [s for s in sents if CAUSE_WORDS.search(s) and not FIX_WORDS.search(s)]
    fix = [s for s in sents if FIX_WORDS.search(s)]
    root_cause = " ".join(cause[:2]) if cause else (sents[0] if sents else text)

    title = sents[0] if sents else text
    if len(title) > 110:
        title = title[:107].rsplit(" ", 1)[0] + "…"

    low = text.lower()
    symptoms = [label for pattern, label in SYMPTOM_RULES if re.search(pattern, low)]
    if not symptoms:
        symptoms = ["service degradation"]

    if P3_WORDS.search(text):
        severity = "P3"
    elif P1_WORDS.search(text):
        severity = "P1"
    else:
        severity = "P2"

    dm = DURATION_RE.search(text)
    duration = f"{dm.group(2)} {dm.group(3)}" if dm else ""

    return {
        "category": category,
        "summary": title,
        "symptoms": symptoms[:5],
        "root_cause": root_cause,
        "resolution": " ".join(fix[:2]),
        "recommended_action": DEFAULT_ACTION[category],
        "severity": severity,
        "duration": duration,
    }


LLM_SYSTEM = (
    "You normalize public production-outage postmortems into a structured incident record "
    "for an SRE knowledge base. Use ONLY facts stated in the summary; if something isn't "
    "stated (for example how it was fixed), return an empty string for that field. "
    "Respond as JSON with keys: summary (<=15 word title), category, symptoms (list of 2-5 "
    "short observable symptoms), root_cause (1-2 sentences), resolution (1-2 sentences or \"\"), "
    "recommended_action, severity (P1 = broad/complete outage, P2 = significant degradation, "
    "P3 = limited impact).\n"
    f"category must be one of: {', '.join(CATEGORIES)}.\n"
    f"recommended_action must be one of: {', '.join(ALLOWED_ACTIONS)}."
)


def daily_limit_hit(llm) -> bool:
    """True when the provider says the per-day token/request quota is used up.
    Retrying is pointless until the quota resets, so the build stops early."""
    err = (getattr(llm, "last_error", None) or "").lower()
    return "per day" in err or "(tpd)" in err or "(rpd)" in err


def llm_extract(llm, entry: dict, hint: dict) -> dict | None:
    user = (
        f"Company: {entry['company']}\n"
        f"Section in source list: {entry['section']}\n"
        f"Postmortem summary: {entry['description']}\n\n"
        f"Rule-based hints (override if wrong): category={hint['category']}, "
        f"severity={hint['severity']}"
    )
    # Reasoning models (e.g. gpt-oss on Groq) spend part of the budget thinking
    # before answering, so leave plenty of room and retry once on bad JSON.
    # gpt-oss models "think" before answering; low effort is plenty for
    # field extraction and uses far fewer tokens (matters on Groq's free tier).
    extra = {"reasoning_effort": "low"} if "gpt-oss" in (llm.model or "") else {}
    out = None
    for _ in range(2):
        out = llm.generate_json(LLM_SYSTEM, user, max_tokens=2500, **extra)
        if isinstance(out, dict) or daily_limit_hit(llm):
            break
    if not isinstance(out, dict):
        return None
    rec = dict(hint)
    for key in ("summary", "root_cause", "resolution"):
        if isinstance(out.get(key), str):
            rec[key] = out[key].strip()
    if isinstance(out.get("symptoms"), list) and out["symptoms"]:
        rec["symptoms"] = [str(s).strip() for s in out["symptoms"]][:5]
    if out.get("category") in CATEGORIES:
        rec["category"] = out["category"]
    if out.get("recommended_action") in ALLOWED_ACTIONS:
        rec["recommended_action"] = out["recommended_action"]
    if out.get("severity") in ("P1", "P2", "P3"):
        rec["severity"] = out["severity"]
    return rec


def entry_key(entry: dict) -> str:
    """Stable cache key: the same postmortem text always maps to the same key."""
    raw = f"{entry['source_url']}\n{entry['description']}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def load_cache(path: Path) -> dict:
    """Read LLM results saved by earlier (possibly interrupted) runs."""
    cache = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                cache[row["key"]] = row["record"]
            except (json.JSONDecodeError, KeyError):
                continue  # a half-written last line from a killed run
    return cache


class TokenPacer:
    """Keeps LLM usage under a tokens-per-minute budget (Groq free tier: 8000 TPM)
    by waiting after each call in proportion to the tokens it used."""

    def __init__(self, llm, tpm: int):
        self.llm, self.tpm = llm, tpm
        self.last_total = llm._total_tokens

    def wait(self):
        used = self.llm._total_tokens - self.last_total
        self.last_total = self.llm._total_tokens
        if self.tpm > 0 and used > 0:
            time.sleep(used / self.tpm * 60)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(SOURCE_SNAPSHOT) if SOURCE_SNAPSHOT.exists() else None,
                    help="Local copy of the post-mortems README "
                         "(default: the pinned snapshot in data/raw/, else download)")
    ap.add_argument("--download", action="store_true", help="Fetch the latest list instead of the pinned snapshot")
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--no-llm", action="store_true", help="Use rule-based extraction only")
    ap.add_argument("--limit", type=int, default=0, help="Only process the first N entries")
    ap.add_argument("--tpm", type=int, default=6500,
                    help="LLM tokens-per-minute budget to stay under (0 = no pacing)")
    ap.add_argument("--fresh", action="store_true", help="Ignore saved LLM progress and redo everything")
    args = ap.parse_args()

    entries = parse_entries(fetch_source(None if args.download else args.source))
    if args.limit:
        entries = entries[: args.limit]
    print(f"Parsed {len(entries)} postmortems")

    # LLM results are appended to this file one by one, so an interrupted run
    # (closed laptop, crash, rate limit) resumes where it stopped.
    cache_path = Path(args.out).with_suffix(".progress.jsonl")
    if args.fresh and cache_path.exists():
        cache_path.unlink()
    cache = load_cache(cache_path)

    llm = None
    if not args.no_llm:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        except ImportError:
            pass
        from src.agent.llm_client import LLMClient
        client = LLMClient()
        if client.is_active:
            llm = client
            print(f"LLM extraction: {client.provider} / {client.model}")
        else:
            print("No LLM configured; using rule-based extraction")

    results = {}  # key -> (record, method)
    if llm:
        pacer = TokenPacer(llm, args.tpm)
        todo = [e for e in entries if entry_key(e) not in cache]
        print(f"Resuming: {len(entries) - len(todo)} already done, {len(todo)} to go")
        # Two passes: anything that failed the first time (rate limit, network
        # drop after sleep) gets one more try at the end.
        stopped_early = False
        for attempt in (1, 2):
            if attempt == 2:
                todo = [e for e in todo if entry_key(e) not in cache]
                if not todo:
                    break
                print(f"Retrying {len(todo)} entries that failed…")
                time.sleep(30)
            with open(cache_path, "a", encoding="utf-8") as fh:
                for n, entry in enumerate(todo, 1):
                    key = entry_key(entry)
                    enriched = llm_extract(llm, entry, rule_extract(entry))
                    if enriched:
                        cache[key] = enriched
                        fh.write(json.dumps({"key": key, "record": enriched}, ensure_ascii=False) + "\n")
                        fh.flush()
                    status = "llm" if enriched else "failed"
                    print(f"  [pass {attempt} · {n}/{len(todo)}] {entry['company']} ({status}) "
                          f"· total done {len(cache)}/{len(entries)}", flush=True)
                    if daily_limit_hit(llm):
                        stopped_early = True
                        break
                    pacer.wait()
            if stopped_early:
                print("\nDaily LLM quota reached. Progress is saved; run the same command "
                      "again after the quota resets to continue.")
                break

    records, llm_used = [], 0
    for i, entry in enumerate(entries, 1):
        rec, method = rule_extract(entry), "rules"
        cached = None if args.no_llm else cache.get(entry_key(entry))
        if cached:
            # Records can carry their own provenance (e.g. "claude" for entries
            # normalized by Claude when the Groq daily quota ran out).
            rec, method, llm_used = cached, cached.get("_extraction", "llm"), llm_used + 1
        records.append({
            "id": f"PM-{i:03d}",
            "company": entry["company"],
            "source_url": entry["source_url"],
            "source": "danluu/post-mortems",
            "section": entry["section"],
            "category": rec["category"],
            "summary": rec["summary"],
            "description": entry["description"],
            "symptoms": rec["symptoms"],
            "logs_signature": ", ".join(rec["symptoms"]),
            "root_cause": rec["root_cause"],
            "resolution": rec["resolution"],
            "recommended_action": rec["recommended_action"],
            "severity": rec["severity"],
            "duration": rec["duration"],
            "extraction": method,
        })

    Path(args.out).write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = Counter(r["category"] for r in records)
    print(f"\nWrote {len(records)} incidents to {args.out} ({llm_used} LLM-normalized, "
          f"{len(records) - llm_used} rule-based)")
    if llm and llm_used < len(records):
        print("Run the same command again to retry the rule-based ones; finished entries are skipped.")
    for cat in CATEGORIES:
        print(f"  {cat:<16} {counts.get(cat, 0)}")


if __name__ == "__main__":
    main()
