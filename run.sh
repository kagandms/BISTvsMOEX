#!/usr/bin/env bash
# Eurasian Bridge Dashboard Launcher
# Run from the repository root with: ./run.sh
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8501}"

if [[ -x ".venv/bin/streamlit" ]]; then
  exec .venv/bin/streamlit run app.py --server.port "$PORT"
fi

if [[ -x "venv/bin/streamlit" ]]; then
  exec venv/bin/streamlit run app.py --server.port "$PORT"
fi

if command -v streamlit >/dev/null 2>&1; then
  exec streamlit run app.py --server.port "$PORT"
fi

printf 'streamlit is not installed. Run: python3.13 -m venv venv && source venv/bin/activate && pip install -r requirements.txt\n' >&2
exit 127
