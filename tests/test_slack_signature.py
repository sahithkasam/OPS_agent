"""Tests for Slack request-signature verification on /slack/actions."""
import ast
import hashlib
import hmac
import time
from pathlib import Path

# Load just the verifier from api/server.py, without starting the app
# (importing the server builds the engine, RAG index, etc.).
_src = (Path(__file__).resolve().parent.parent / "api" / "server.py").read_text(encoding="utf-8")
_fn = next(n for n in ast.parse(_src).body
           if isinstance(n, ast.FunctionDef) and n.name == "verify_slack_signature")
_ns = {"time": time}
exec(ast.get_source_segment(_src, _fn), _ns)
verify = _ns["verify_slack_signature"]

SECRET = "8f742231b10e8888abcd99yyyzzz85a5"
BODY = b"payload=%7B%22actions%22%3A%5B%5D%7D"


def sign(body: bytes, ts: str, secret: str = SECRET) -> str:
    base = b"v0:" + ts.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def test_valid_signature_accepted():
    ts = str(int(time.time()))
    assert verify(BODY, ts, sign(BODY, ts), SECRET)


def test_tampered_body_rejected():
    ts = str(int(time.time()))
    assert not verify(BODY + b"x", ts, sign(BODY, ts), SECRET)


def test_wrong_secret_rejected():
    ts = str(int(time.time()))
    assert not verify(BODY, ts, sign(BODY, ts, secret="other"), SECRET)


def test_replayed_old_request_rejected():
    old = str(int(time.time()) - 10 * 60)
    assert not verify(BODY, old, sign(BODY, old), SECRET)


def test_missing_headers_rejected():
    assert not verify(BODY, None, None, SECRET)
    assert not verify(BODY, "not-a-number", "v0=abc", SECRET)
