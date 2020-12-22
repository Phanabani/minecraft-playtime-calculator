#!/bin/bash
dir="$(dirname "${BASH_SOURCE[0]}")"
if [[ -d "$dir/venv" ]]; then
  echo "It looks like setup has already been run. You should be good to go!"
else
  echo "Beginning setup"
  echo "Creating virtual environment from system Python"
  python3 -m venv "$dir/venv"
  source "$dir/venv/bin/activate"
  echo "Installing dependencies"
  python3 -m pip install -r "$dir/requirements.txt"
  echo "Setup complete!"
fi
