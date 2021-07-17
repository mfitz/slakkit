import json
import os
import random

import boto3
import requests
import slack


def lambda_handler(event, context):
    print("Reading SlackIt configuration from env vars....")
    target_channel = os.environ.get('slackit_TARGET_CHANNEL')
    oauth_secret_name = os.environ.get('slackit_OAUTH_SECRET_NAME')
    slack_oauth_token = get_secret(oauth_secret_name).get('api_key')
    subreddit_list = os.environ.get('slackit_SUBREDDIT_LIST').split(',')

    reddits = get_random_reddits(subreddit_list)
    reddit = choose_a_reddit(reddits['data']['children'])
    slack_blocks = make_slack_message_blocks(reddit)
    send_slack_message(target_channel, slack_oauth_token, slack_blocks)


def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    print("Looking for secret '{}' in Secrets Manager".format(secret_name))
    response = client.get_secret_value(SecretId=secret_name)
    if 'SecretString' in response:
        print("Found string secret for '{}'".format(secret_name))
        return json.loads(response['SecretString'])
    else:
        raise ValueError("Did not find an appropriate secret under the name '{}'".format(secret_name))


def make_slack_message_blocks(reddit):
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "> {}".format(reddit['data']['title'])
            }
        },
        {
            "type": "image",
            "image_url": "{}".format(reddit['data']['url_overridden_by_dest']),
            "alt_text": "marg"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Pulled from the <{}|{}> subreddit".format(
                    'https://www.reddit.com{}'.format(reddit['data']['permalink']),
                    reddit['data']['subreddit'])
            }
        },
        {
            "type": "divider"
        }
    ]


def send_slack_message(channel, api_token, blocks):
    print('Sending slack message to {} channel...'.format(channel))
    response = slack.WebClient(api_token).chat_postMessage(
        channel=channel,
        blocks=blocks
    )
    print('Slack API response {}'.format(response))


def get_random_reddits(subreddit_list):
    subreddit = random.choice(subreddit_list)
    print("Retrieving top posts from {}".format(subreddit))
    url = "https://www.reddit.com/r/{}/top.json?limit=30&t=month".format(subreddit)
    print("Requesting {}".format(url))
    response = requests.get(url, headers={'User-agent': 'SlackIt 0.1'})
    print("Got response {}".format(response))
    return response.json()


def choose_a_reddit(reddit_list):
    print("Selecting a reddit from a list of {}".format(len(reddit_list)))
    random.shuffle(reddit_list)
    for reddit in reddit_list:
        if reddit['data']['title'] \
                and reddit['data']['url_overridden_by_dest'] \
                and not reddit['data']['is_video'] \
                and ('is_gif' not in reddit['data'] or not reddit['data']['is_gif']) \
                and ('is_gallery' not in reddit['data'] or not reddit['data']['is_gallery']):
            print("Selected a reddit from the list of reddits: {}".format(reddit))
            return reddit
    raise ValueError('Could not find a reddit with a title and picture from this list of reddits: {}'
                     .format(reddit_list))


if __name__ == '__main__':
    lambda_handler('Command line event', 'Command line context')
