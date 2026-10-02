# Windows
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
docker build -t tcg-exemple .
if ($LASTEXITCODE -ne 0) { exit 1 }
docker rm -f tcg-exemple 2>$null | Out-Null
# .env holds OPENROUTER_API_KEY; without it the app runs and only the AI chat is unavailable.
$envFile = @()
if (Test-Path .env) { $envFile = @("--env-file", ".env") }
docker run -d --name tcg-exemple -p 8000:8000 @envFile -v tcg-exemple-data:/data tcg-exemple
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "TCG-exemple : http://localhost:8000 (utilisateur : user / mot de passe : user)"
