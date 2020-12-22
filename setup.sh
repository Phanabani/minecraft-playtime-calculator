if [[ -d venv ]]; then
  echo "It looks like setup has already been run. You should be good to go!"
else
  echo "Beginning setup"
  echo "Creating virtual environment from system Python"
  python -m venv venv
  source venv/bin/activate
  echo "Installing dependencies"
  python -m pip install -r requirements.txt
  echo "Setup complete!"
fi
