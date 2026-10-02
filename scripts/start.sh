#!/usr/bin/env bash
# Mac and Linux
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t tcg-exemple .
docker rm -f tcg-exemple >/dev/null 2>&1 || true
docker run -d --name tcg-exemple -p 8000:8000 --env-file .env -v tcg-exemple-data:/data tcg-exemple
echo "TCG-exemple : http://localhost:8000 (utilisateur : user / mot de passe : user)"
