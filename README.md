# Slakkit
Summarise top Reddit photo posts in Slack messages.

Slakkit can be deployed into AWS as a Lambda function, or run locally as a regular Python application. Every time
Slakkit runs, it randomly chooses a single subreddit from the list supplied as config, grabs the top posts from that
subreddit, shuffles them into random order, then selects the first post that is a photo and posts it to Slack as a
simple message using the title of the post, the photo, and a hyperlink to the post on the Reddit website.

<kbd><img src="readme-images/cat-reddit-1.png"/></kbd>

<kbd><img src="readme-images/cat-reddit-2.png"/></kbd>


## Prerequisites
- Python 3.8.1 or greater
- A list of Reddit subreddits you want to read from
- Admin permissions on your AWS Account
- A Slack app and associated User OAuth Token (or permissions enough to create new apps in your Slack space)


## Installing
You must create a virtual environment, otherwise the build script will complain (it uses the venv to figure out what
to bundle into the deployment artefact). I highly recommend [PyEnv](https://github.com/pyenv/pyenv) for managing Python
virtual environments, or you could go low tech and do something like:

```bash
 $ python3 -m venv venv
 $ source venv/bin/activate
 $ pip install -r requirements.txt
 $ pip install -r dev-requirements.txt
```

If you only plan to build the deployment artefact, rather than run Slakkit locally or make dev changes, you don't need
to install `dev-requirements.txt`; `requirements.txt` will be sufficient.


## Running locally
When you run Slakkit locally, you can choose to pass the Slack app's OAuth token directly as an env var, or indirectly,
whereby the value of the env var is the name under which the token is stored in AWS Secrets Manager. If you use the
indirect Secrets Manager option, you must be invoking Slakkit from within an authenticated shell that has permissions
to read the token secret from Secrets Manager.

```bash
slakkit_TARGET_CHANNEL="my-awesome-channel" \
slakkit_OAUTH_TOKEN="xoxb-01234567890-01234567890123-ABcDefGhIJ1klMnoPqrstuvw" \
slakkit_SUBREDDIT_LIST="IllegallySmolCats,CatsInBusinessAttire,blackcats,cats" \
python main.py
```


## Building the deployment artefact
To create the zip file to upload to the Lambda environment, from the project root and inside an active virtual env:

```bash
$ ./build-lambda.sh

Backing up virtual env's current dependency list...
Clearing out the virtual env...
Uninstalling aiohttp-3.7.4.post0:
  Successfully uninstalled aiohttp-3.7.4.post0
Uninstalling async-timeout-3.0.1:
  Successfully uninstalled async-timeout-3.0.1
Uninstalling attrs-21.2.0:
  Successfully uninstalled attrs-21.2.0
...
```

```bash
$ ls -talh *zip

-rw-r--r--  1 mickyfitz  staff   6.1M 20 Jul 01:28 slakkit-lambda.zip
```
The build script:

- backs up the contents of your venv
- cleans out the venv completely
- installs into the venv only the minimal set of production dependencies as found in `requirements.txt` - so no
`pytest`, `flake8` or `boto3` (which is already installed in the AWS Lambda runtime), etc.
- bundles up all of the libraries in the venv plus our own code into a deployment artefact (a zip file)
- restores your venv to its pre-build state using the backup


## Deploying to AWS Lambda
Create the deployment zip file as per [#building-the-deployment-artefact](Building the deployment artefact).

