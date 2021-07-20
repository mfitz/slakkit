# Slakkit
Summarise top Reddit photo posts in Slack messages.

Slakkit can be deployed into AWS as a Lambda function, or run locally as a regular Python application. Every time
Slakkit runs, it randomly chooses a single subreddit from the list supplied as config, grabs the top posts from that
subreddit, shuffles them into random order, and selects the first post that is a photo. This selected post is used to
make a simple Slack message featuring the title of the post, the photo, and a hyperlink to the Reddit website.

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


## Deploying to AWS Lambda

### Slack API Credentials
You **must** add your Slack app's OAuth token (revealed after creating and installing the Slack app) to AWS Secrets
Manager **in the same AWS account and region** that the Slakkit Lambda will be deployed to. You can name the secret
whatever you like in Secrets Manager; the name of the secret will later be set as an environmental variable read by
the Lambda at runtime. However, a name like `slakkit/slack-oauth-token` makes it clear what the secret is for.

I added the secret manually via
[the AWS console](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_create-basic-secret.html)
, but you could equally use the AWS CLI (see `aws secretsmanager create-secret help`). Select `Other type of secrets
(e.g. API key)` as the key type in the console.

The secret **must** contain a name/value pair `api_key:<Slack OAuth token value>`; the Slakkit Lambda expects
to retrieve a dictionary from Secrets Manager using the name you supplied and will then interrogate this dictionary
for the value of `api_key`. So in plain text, your secret's value should look like:
```json
{"api_key": "xoxb-01234567890-01234567890123-ABcDefGhIJ1klMnoPqrstuvw"}
```

### Building the deployment artefact
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

### Creating and configuring the Lambda function
Browse to the Lambda UI in the AWS console, which you can find at a URL like (adjust your region accordingly)
`https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/functions`. Create a new function, upload the
zip file, and manually configure the Lambda with the following settings, allowing the Lambda wizard to create a new
execution role for you:

```json
{
  "Configuration": {
    "FunctionName": "cats-slakkit",
    "MemorySize": 128,
    "PackageType": "Zip",
    "FunctionArn": "arn:aws:lambda:eu-west-1:123456789012:function:cats-slakkit",
    "Environment": {
      "Variables": {
        "slackit_OAUTH_SECRET_NAME": "slakkit/slack_oauth_token",
        "slackit_SUBREDDIT_LIST": "IllegallySmolCats,CatsInSinks,cats,Blep",
        "slackit_TARGET_CHANNEL": "some-channel"
      }
    },
    "Handler": "main.lambda_handler",
    "Role": "arn:aws:iam::123456789012:role/service-role/cats-slakkit-role-44dl7jp9",
    "Timeout": 20,
    "Runtime": "python3.8"
  }
}
```

When the newly created execution role exists, add a policy granting permission to read the OAuth token from Secrets
Manager, for example:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetResourcePolicy",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecretVersionIds"
            ],
            "Resource": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:slackit/*"
        }
    ]
}
```

### Scheduling the Lambda function
AWS Lambda is an event-driven environment. You can trigger the Slakkit Lambda function using a
[Cloudwatch Rule](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/Create-CloudWatch-Events-Rule.html)
running on a cron-like schedule in order to automatically run Slakkit at various times of the day/week/month/year. In
the Lambda console, select `Triggers > Add trigger` and select `EventBridge (CloudWatch Events)`. Select `Create a new
rule` and choose `Schedule expression` as the `Rule type` and use something like `cron(0 14 * * ? *)` as the
`Schedule expression`, where `14` is the hour of each day in UTC that you want the Lambda to be triggered. The
`schedule_expression` can be anything supported by
[CloudWatch Events schedule syntax](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents-expressions.html)
, so you can choose to run every `n` minutes or hours, at specified times on specified days, etc.
