# Expose the local backend to Slack so the Approve / Escalate buttons work locally.
#
# Starts a free Cloudflare "quick tunnel" (no account needed) to http://localhost:8000,
# writes the public callback URL into .env as SLACK_CALLBACK_URL, and prints the
# Request URL to paste into your Slack app (Interactivity & Shortcuts).
#
# Usage (from the project root, with the backend already running on port 8000):
#     powershell -ExecutionPolicy Bypass -File scripts\slack_tunnel.ps1
#
# The quick-tunnel URL changes every time this runs, so paste the new URL into Slack each time.
# Stop the tunnel with Ctrl+C.

param([int]$Port = 8000)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root '.env'

# 1. Find cloudflared
$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf) {
    foreach ($p in @("$env:ProgramFiles\cloudflared\cloudflared.exe",
                     "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe")) {
        if (Test-Path $p) { $cf = $p; break }
    }
}
if (-not $cf) {
    Write-Host "cloudflared is not installed. Install it with:" -ForegroundColor Yellow
    Write-Host "    winget install --id Cloudflare.cloudflared"
    Write-Host "then open a NEW terminal and run this script again."
    exit 1
}

# 2. Check the backend is up
try {
    Invoke-RestMethod "http://localhost:$Port/api/health" -TimeoutSec 3 | Out-Null
} catch {
    Write-Host "Backend is not responding on http://localhost:$Port." -ForegroundColor Yellow
    Write-Host "Start it first:  uvicorn api.server:app --reload --port $Port"
    exit 1
}

# 3. Start the tunnel and wait for its public URL
$log = Join-Path $env:TEMP "cloudflared-ops-agent.log"
if (Test-Path $log) { Remove-Item $log -Force }
$proc = Start-Process -FilePath $cf -ArgumentList @('tunnel', '--url', "http://localhost:$Port") `
    -RedirectStandardError $log -NoNewWindow -PassThru

$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $log) {
        $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value }
    }
    if ($proc.HasExited) { break }
}
if (-not $url) {
    Write-Host "Could not get a tunnel URL. cloudflared log: $log" -ForegroundColor Red
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    exit 1
}
$callback = "$url/slack/actions"

# 4. Save it to .env (replace the SLACK_CALLBACK_URL line, or add one)
$lines = if (Test-Path $envFile) { @(Get-Content $envFile) } else { @() }
if ($lines -match '^SLACK_CALLBACK_URL=') {
    $lines = $lines -replace '^SLACK_CALLBACK_URL=.*$', "SLACK_CALLBACK_URL=$callback"
} else {
    $lines += "SLACK_CALLBACK_URL=$callback"
}
[System.IO.File]::WriteAllLines($envFile, $lines)

$hasSecret = [bool]($lines | Where-Object { $_ -match '^SLACK_SIGNING_SECRET=.+' })

Write-Host ""
Write-Host "Tunnel is up." -ForegroundColor Green
Write-Host "Paste this into Slack -> your app -> Interactivity & Shortcuts -> Request URL:"
Write-Host ""
Write-Host "    $callback" -ForegroundColor Cyan
Write-Host ""
Write-Host "Saved to .env as SLACK_CALLBACK_URL."
if (-not $hasSecret) {
    Write-Host "Tip: set SLACK_SIGNING_SECRET in .env (Slack app -> Basic Information) and restart" -ForegroundColor Yellow
    Write-Host "     the backend, so only genuine Slack clicks can approve incidents."
}
Write-Host ""
Write-Host "Keep this window open. Press Ctrl+C to stop the tunnel."

try {
    Wait-Process -Id $proc.Id
} finally {
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
}
