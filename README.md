# Slakkit

<script id="asciicast-443899" src="https://asciinema.org/a/443899.js" async></script>

<img src="readme-images/slakkit-icon-512.png" width="100" height="100"/>

Slakkit turns Reddit image posts into Slack messages.

## Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installing](#installing)
- [Creating Slack apps](#creating-slack-apps)
- [Running locally](#running-locally)
- [Randomness and duplicate posts](#randomness-and-duplicate-posts)
- [Deploying to AWS Lambda](#deploying-to-aws-lambda)
  - [Slack API Credentials](#slack-api-credentials)
  - [Building the deployment artefact](#building-the-deployment-artefact)
  - [Creating and configuring the Lambda function](#creating-and-configuring-the-lambda-function)
    - [Lambda permissions](#lambda-permissions)
  - [Scheduling the Lambda function](#scheduling-the-lambda-function)

## Introduction
Slakkit can be deployed into AWS as a [Lambda function](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html),
or run locally (or anywhere else) as a regular Python application. Every time Slakkit runs, it randomly chooses a
single subreddit from a list supplied as config, grabs the top posts from that subreddit, shuffles them into random
order, and selects the first post that is an image. This selected post is used to make a simple Slack message
featuring the title of the post, the image, and a hyperlink to the post on the Reddit website.

<kbd><img src="readme-images/cat-reddit-1.png" width="650"/></kbd>

<kbd><img src="readme-images/cat-reddit-2.png" width="650"/></kbd>

<kbd><img src="readme-images/cat-reddit-3.png" width="650"/></kbd>


## Prerequisites
- Python 3.8.1 or greater (_probably_ works with other Python 3 versions, but `3.8.1` is the only one I've used with it)
- A list of Reddit subreddits you want to read from
- An existing Slack app and associated User OAuth Token, or permissions enough to [create new apps in your Slack space](#creating-slack-apps)
- (If you are deploying to Lambda) Admin permissions on your AWS Account, or at least permissions enough to
create new Lambda functions and CloudWatch rules


## Installing
If you want to deploy Slakkit to AWS Lambda, you **must** install into a local virtual environment, otherwise the
[lambda build script](#building-the-deployment-artefact) will complain (it uses the venv to figure out
what to bundle up into the deployment artefact). In any case, using a virtual environment is
[generally a good idea](https://towardsdatascience.com/why-you-should-use-a-virtual-environment-for-every-python-project-c17dab3b0fd0).
I highly recommend [PyEnv](https://github.com/pyenv/pyenv) for managing Python virtual environments, or you
could go low tech and do something like:

```bash
 $ python3 -m venv venv
 $ source venv/bin/activate
 $ pip install -r requirements.txt
 $ pip install -r dev-requirements.txt # only if you will be running locally and/or making dev changes
```

If you only plan to build the Lambda deployment artefact, rather than run Slakkit locally or make dev changes,
you don't need to install `dev-requirements.txt`; `requirements.txt` will be sufficient.


## Creating Slack apps
To create a new Slack app, use the [Slack web UI](https://api.slack.com/apps?new_app=1). It's
fairly self-explanatory, and there are
[online guides available to help](https://api.slack.com/authentication/basics#creating) if you
need them.

Having created your Slack app you will then need to configure it thus:

`Add features and functionality > Permissions > Scopes > Bot Token Scopes:` Add OAuth Scopes for `chat:write` &
`chat:write.public`

Once you have added these permissions, you will be able to click to "install" the app. You will then
have access to an OAuth Access Token, which you need to make available to Slakkit at runtime, either
[via AWS Secrets Manager](#slack-api-credentials), or by passing the value directly as an environmental
variable.

You should also edit the app's `Display Information`, upload an app icon, and ideally set up some
`Collaborators` who will be able to administer the app alongside you.


## Running locally
See [Creating Slack apps](#creating-slack-apps) for instructions on how to create your Slack app and generate an OAuth
token. When you run Slakkit locally, you can choose to pass the Slack app's OAuth token directly as an env var, or
indirectly, whereby the value of the env var is the name under which the token is stored in AWS Secrets Manager. If you
use the indirect Secrets Manager option, you must be invoking Slakkit from within an authenticated shell that has
permissions to read the token secret from Secrets Manager.

**Passing the Slack OAuth token directly:**
```bash
slakkit_TARGET_CHANNEL="my-awesome-channel" \
slakkit_OAUTH_TOKEN="xoxb-01234567890-01234567890123-ABcDefGhIJ1klMnoPqrstuvw" \
slakkit_SUBREDDIT_LIST="IllegallySmolCats,CatsInBusinessAttire,blackcats,cats" \
python main.py
```

**Passing the Slack OAuth token via AWS Secrets Manager:**
```bash
slakkit_TARGET_CHANNEL="my-awesome-channel" \
slakkit_OAUTH_TOKEN="slakkit/slack-oauth-token" \
slakkit_SUBREDDIT_LIST="IllegallySmolCats,CatsInBusinessAttire,blackcats,cats" \
python main.py
```

## Randomness and duplicate posts
Slakkit does not keep and interrogate a persistent record of which Reddit posts it has seen, so duplicate messages
are possible, but you can do a few things to make it less likely that you will see them.

In general, the more unique subreddits you have in `slakkit_SUBREDDIT_LIST`, the less chance there will be of duplicate
messages, so a longer list is _usually_ better. However, there are circumstances where this rule of thumb does not hold,
because subreddits with low levels of activity are more likely to return the same or a very similar list of top posts
each time you query them. By contrast, the list of top posts for a very busy subreddit changes regularly. For this
reason, including only, or mostly, "busy" subreddits in your list reduces the chance of duplicate messages.

You can also ensure some subreddits are more likely to be randomly chosen, and therefore likely to be used more often,
simply by repeating the subreddits you want to favour. For example, using the following list makes it twice as likely
that the subreddit `IllegallySmolCats` will be chosen, meaning that over time you can expect twice as many posts to be
pulled from that subreddit compared to the others.

`slakkit_SUBREDDIT_LIST="IllegallySmolCats,CatsInBusinessAttire,blackcats,cats,IllegallySmolCats"`

If `IllegallySmolCats` is a very busy subreddit relative to the others in the list, this approach would help reduce
the chances of seeing duplicate messages. Outside of any concerns about duplication, you can of course also use
this tactic when you simply want more posts from a particular subreddit. Maybe you just like illegally small cats.

By default, Slakkit queries the Reddit API using a page size of 50, meaning a maximum of 50 posts from the chosen
subreddit will be returned. You can override this value using the `slakkit_REDDIT_PAGE_SIZE` environmental variable,
e.g. `slakkit_REDDIT_PAGE_SIZE=75`. In general, the bigger the page size, the less chance of Slakkit randomly choosing
a Reddit post that has already been seen.

## Deploying to AWS Lambda
The AWS Lambda environment [automatically retries twice on failure](https://aws.amazon.com/about-aws/whats-new/2019/11/aws-lambda-supports-max-retry-attempts-event-age-asynchronous-invocations/)
for functions invoked from Cloudwatch rules, so deploying Slakkit to Lambda as described below is a nice way to get some
free resilience.

### Slack API Credentials
Unless you plan to pass your Slack app's OAuth token directly as an env var, you **must** add it to AWS Secrets
Manager **in the same AWS account and region** that the Slakkit Lambda will be deployed to. You can name the
secret whatever you like in Secrets Manager; the name of the secret will later be set as an environmental variable
read by the Lambda at runtime. However, a descriptive name like `slakkit/slack-oauth-token` makes it clear what
the secret is for.

I tend to add secrets to Secrets Manager manually via
[the AWS console](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_create-basic-secret.html)
, but you can also use the [AWS CLI](https://aws.amazon.com/cli/) (see `aws secretsmanager create-secret help`).
Select `Other type of secrets (e.g. API key)` as the key type in the console.

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
dev dependencies like `pytest`, `flake8` or `boto3` (which is already installed in the AWS Lambda runtime), etc.
- bundles up all of the libraries in the venv plus Slakkit's own Python code into a deployment artefact (a zip file)
- restores your venv to its pre-build state using the backup

### Creating and configuring the Lambda function
Browse to the Lambda UI in the AWS console, which you can find at a URL like (adjust your region accordingly)
`https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/functions`. Create a new function, and upload
the zip file. You should allow the Lambda wizard to create a new execution role for you, and configure the Lambda
with the following settings:

```json
{
  "Configuration": {
    "FunctionName": "cats-slakkit",
    "MemorySize": 128,
    "PackageType": "Zip",
    "FunctionArn": "arn:aws:lambda:eu-west-1:123456789012:function:cats-slakkit",
    "Environment": {
      "Variables": {
        "slakkit_OAUTH_TOKEN": "slakkit/slack_oauth_token",
        "slakkit_SUBREDDIT_LIST": "IllegallySmolCats,CatsInSinks,cats,Blep",
        "slakkit_TARGET_CHANNEL": "some-channel"
      }
    },
    "Handler": "main.lambda_handler",
    "Role": "arn:aws:iam::123456789012:role/service-role/cats-slakkit-role-44dl7jp9",
    "Timeout": 20,
    "Runtime": "python3.8"
  }
}
```

You can create an arbitrarily long list of subreddits of interest as the value of the `slakkit_SUBREDDIT_LIST` env var.
Longer lists are [usually better for avoiding duplicate posts](#randomness-and-duplicate-posts). You must:

- use only the short names of subreddits (rather than complete URLs), so `IllegallySmolCats`, **not** `https://www.reddit.com/r/IllegallySmolCats/`
- separate the list using commas

Note that when you are creating the list as an environmental variable via the Lambda console, you should not
enclose the list in quotes.

The value of the `slakkit_TARGET_CHANNEL` env var should be only the channel name, with no leading hash character, so
`my-awesome-channel`, **not** `#my-awesome-channel`.

#### Lambda permissions
When the newly created execution role exists, add a policy to it granting permission to read the OAuth
token from Secrets Manager, for example:

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
            "Resource": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:slakkit/*"
        }
    ]
}
```

### Scheduling the Lambda function
AWS Lambda is an event-driven environment. You can trigger the Slakkit Lambda function using events generated
by a [Cloudwatch Rule](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/Create-CloudWatch-Events-Rule.html)
running on a cron-like schedule, allowing you to automatically run Slakkit at various times of the day/week/month/year.
In the Lambda console, select `Triggers > Add trigger` and select `EventBridge (CloudWatch Events)`. Select `Create
a new rule`, choose `Schedule expression` as the `Rule type` and use something like `cron(0 14 * * ? *)` as the
`Schedule expression`, where `14` is the hour of each day in UTC that you want the Lambda to be triggered. 

The `schedule_expression` can be anything supported by
[CloudWatch Events schedule syntax](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents-expressions.html)
, so you can choose to run every `n` minutes or hours, or at specified times on specified days, etc. You can create
as many different rules as you like and point them all at the same Lambda function, so you can create as complicated
a schedule as you want for running Slakkit.
