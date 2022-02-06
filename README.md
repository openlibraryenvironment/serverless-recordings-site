# Serverless Generator for Zoom Recordings Site

## Development Environment Set-up

See [Starting a Python-oriented Serverless-dot-com Project](https://dltj.org/article/starting-python-serverless-project/) for details.

1. `git clone serverless-template && cd serverless-template`
1. `PIPENV_VENV_IN_PROJECT=1 pipenv install --dev`
1. `pipenv shell` 
1. `nodeenv -p` # Installs Node environment inside Python environment
1. `npm install --include=dev` # Installs Node packages inside combined Python/Node environment
1. `exit` # For serverless to install correctly in the environment...
1. `pipenv shell` # ...we need to exit out and re-enter the environment
1. `npm install -g serverless` # Although the '-g' global flag is being used, Serverless install is in the Python/Node environment

