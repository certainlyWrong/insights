#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "Erro: uv não encontrado. Instale em https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Erro: npm não encontrado. Instale o Node.js em https://nodejs.org/" >&2
  exit 1
fi

echo "Preparando ambiente Python..."
uv sync

if [[ ! -x web/node_modules/.bin/vite ]]; then
  echo "Instalando dependências do site..."
  npm ci --prefix web
fi

echo "Atualizando os dados locais do painel..."
uv run python web/scripts/build_data.py

echo "Abrindo Insights em http://127.0.0.1:5173"
exec npm --prefix web run dev
