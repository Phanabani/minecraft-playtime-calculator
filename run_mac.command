#!/bin/bash
dir="$(dirname "${BASH_SOURCE[0]}")"
if [[ -e venv/bin/activate ]]; then
  source "$dir/venv/bin/activate"
  python3 "$dir/main.py"
else
  echo "You haven't installed the virtual environment yet. Run setup.sh"
fi
