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

## Set Up Public Key for Signing URLs

1. Create a public/private key pair (see [Create a key pair for a trusted key group](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-trusted-signers.html#create-key-pair-and-key-group))
  * `openssl genrsa -out private_key.pem 2048`
  * `openssl rsa -pubout -in private_key.pem -out public_key.pem`
1. Go to [AWS Systems Manager → Parameter Store → Create parameter](https://console.aws.amazon.com/systems-manager/parameters/create) (ensure you are in the correct AWS region)
  * _Name_: `/serverless-recordings-site/dev/private-key`
  * _Description_: `Private key of key-pair for signing URLs`
  * _Tier_: Standard
  * _Type_: Secure String
  * _KMS Key Source_: My current account
  * _KMS Key ID_: `alias/aws/ssm`
  * _Value_: paste private key data
  * _Tag_: `Purpose` → `serverless-recordings-site`
1. In `config.yml`, assign the name to the `PRIVATE_KEY_PARAM_STORE_NAME` attribute
1. In `config.yml`, paste the public key value into the `PUBLIC_KEY_ENCODED` attribute as a YAML multi-line string. Note well [this caution](https://dltj.org/article/cloudformation-invalid-request-cloudfront-publickey/).