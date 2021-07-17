import json
import os
import random

import boto3
import requests
import slack


def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    print("Looking for secret '{}' in Secrets Manager".format(secret_name))
    response = client.get_secret_value(SecretId=secret_name)
    if 'SecretString' in response:
        print("Found string secret for '{}'".format(secret_name))
        return json.loads(response['SecretString'])
    else:
        raise ValueError("Did not find an appropriate secret under the name '{}'".format(secret_name))


def make_slack_message(reddit):
    return {
        "blocks": [
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
                    "text": "Scraped from Reddit's <{}|{}>.".format(
                        'https://www.reddit.com{}'.format(reddit['data']['permalink']),
                        reddit['data']['subreddit'])
                }
            },
            {
                "type": "divider"
            }
        ]
    }


def send_slack_message(channel, api_token, attachments=None, blocks=None):
    print('Sending slack message to {} channel...'.format(channel))
    response = slack.SlackClient(api_token).api_call(
        "chat.postMessage",
        channel=channel,
        attachments=attachments,
        blocks=blocks,
        user="slackit",
    )
    print('Slack API response {}'.format(response))


def get_random_reddits(subreddit_list):
    subreddit = random.choice(subreddit_list)
    print("Retrieving top 10 posts for the day from {}".format(subreddit))
    url = "https://www.reddit.com/r/{}/top.json?limit=10&t=day".format(subreddit)
    print("Requesting {}".format(url))
    response = requests.get(url, header={'User-agent': 'SlackIt 0.1'})
    print("Got response {}".format(response))
    return response.json()


def choose_a_reddit(reddit_list):
    for reddit in reddit_list:
        if reddit['data']['title'] and reddit['data']['url_overridden_by_dest']:
            print("Selected a reddit from the list of reddits: {}".format(reddit))
            return reddit
    raise ValueError('Could not find a reddit with a title and picture from this list of reddits: {}'
                     .format(reddit_list))


if __name__ == '__main__':
    print("Reading SlackIt configuration from env vars....")
    target_channel = os.environ.get('slackit.TARGET_CHANNEL')
    oauth_secret_name = os.environ.get('slackit.OAUTH_SECRET_NAME')
    slack_oauth_token = get_secret(oauth_secret_name)
    subreddit_list = os.environ.get('slackit.SUBREDDIT_LIST').split(',')

    reddit_json = get_random_reddits(subreddit_list)
    reddit = choose_a_reddit(subreddit_list['data']['children'])
    slack_blocks = make_slack_message(reddit)
    send_slack_message(target_channel, slack_oauth_token, blocks=slack_blocks)
