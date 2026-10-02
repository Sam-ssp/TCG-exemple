#!/usr/bin/env bash
# Mac and Linux
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t tcg-exemple .
docker rm -f tcg-exemple >/dev/null 2>&1 || true
# .env holds OPENROUTER_API_KEY; without it the app runs and only the AI chat is unavailable.
env_file=()
[ -f .env ] && env_file=(--env-file .env)
docker run -d --name tcg-exemple -p 8000:8000 ${env_file[@]+"${env_file[@]}"} -v tcg-exemple-data:/data tcg-exemple
echo "TCG-exemple : http://localhost:8000 (utilisateur : user / mot de passe : user)"
