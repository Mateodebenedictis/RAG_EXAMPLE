# Сaylent [![Build Status](https://app.travis-ci.com/subatomicsystems/caylent.svg?token=KPBLjzU1725Wp9wjjA3a&branch=dev)](https://app.travis-ci.com/subatomicsystems/caylent)

Sentry - https://storied.sentry.io/projects/caylent/getting-started/

## Local development

### Pre-requisites

Python 3. The suggested installation method is via [pyenv](https://github.com/pyenv/pyenv#installation) or
[asdf](https://asdf-vm.com/guide/getting-started.html).

### Setup

1. Create a virtual environment:
    ```shell
    python -m venv ./venv
   ```
2. Install all requirements, **including dev requirements**:
    ```shell
    pip install -r requirements.txt -r requirements-dev.txt
   ```
3. Install pre-commit:
    ```shell
    pre-commit install
   ```

## <a name="deployment"></a>Deployment
The AWS infrastructure (Lambda resources) is built on Travis CI.
The deployment cycle takes the following steps:
* Travis CI builds and creates ZIP archive
* Travis CI pushes ZIP archive to S3 bucket
* Travis CI runs CloudFormation template `/arch/lambda.yaml` for creating/updating Lambda function
* Travis CI updates Lambda function via created ZIP archive

Variables should be set before deployment and should be deleted after successful deploy.

### Deployment schedule
| Branch Name | Deployment Schedule              | Update method                         |
|-------------|----------------------------------|---------------------------------------|
| master      | on every commit to master branch | Merge release branch to master branch |
| stage       | on every commit to stage branch  | Merge dev branch to stage branch      |
| fedev       | on every commit to fedev branch  | Merge dev branch to fedev branch      |
| dev         | on every commit to dev branch    | By commit                             |
