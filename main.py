import json
import os
import random

import boto3
import requests
import slack


def lambda_handler(event, context):
    print("Reading Slakkit configuration from env vars....")
    target_channel = os.environ.get('slakkit_TARGET_CHANNEL')
    slack_oauth_token = get_slack_oauth_token()
    subreddit_list = os.environ.get('slakkit_SUBREDDIT_LIST').split(',')

    reddits = get_random_reddits(subreddit_list)
    reddit = choose_a_reddit(reddits['data']['children'])
    slack_blocks = make_slack_message_blocks(reddit)
    send_slack_message(target_channel, slack_oauth_token, slack_blocks)


def get_slack_oauth_token():
    oauth_token = os.environ.get('slakkit_OAUTH_TOKEN')
    if oauth_token.startswith('xoxb-'):
        print("Found Slack OAuth token as env var")
        return oauth_token
    else:
        print("Looking for Slack OAuth token in Secrets Manager at {}".format(oauth_token))
        return get_secret(oauth_token).get('api_key')


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
    blocks = [
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
            "alt_text": "image"
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
    print("Made Slack message blocks: {}".format(blocks))
    return blocks


def send_slack_message(channel, api_token, blocks):
    print('Sending slack message to {} channel...'.format(channel))
    response = slack.WebClient(api_token).chat_postMessage(channel=channel, blocks=blocks)
    print('Slack API response {}'.format(response))


def get_random_reddits(subreddit_list):
    subreddit = random.choice(subreddit_list)
    print("Retrieving top posts from {}".format(subreddit))
    page_size = 50 # TODO - make this overrideable via env var
    request_headers = {'User-agent': 'Slakkit 0.1'}
    url = "https://www.reddit.com/r/{}/top.json?limit={}&t=month".format(subreddit, page_size)
    print("Requesting {}".format(url))
    response = requests.get(url, headers=request_headers)
    print("Got response {}".format(response))
    resp_json = response.json()
    number_of_posts = len(resp_json['data']['children'])
    if number_of_posts < page_size:
        print("Not enough posts in the response, only found {} - asking for more data...".format(number_of_posts))
        url = "https://www.reddit.com/r/{}/top.json?limit={}&t=year".format(subreddit, page_size)
        print("Requesting {}".format(url))
        response = requests.get(url, headers=request_headers)
        print("Got response {}".format(response))
        resp_json = response.json()
        print("New response has {} posts".format(len(resp_json['data']['children'])))
    return resp_json


def choose_a_reddit(reddit_list):
    print("Selecting a reddit from a list of {}".format(len(reddit_list)))
    random.shuffle(reddit_list)
    for reddit in reddit_list:
        if reddit['data']['title'] \
                and reddit['data']['url_overridden_by_dest'] \
                and ('post_hint' in reddit['data'] and reddit['data']['post_hint'] == 'image') \
                and not reddit['data']['is_video'] \
                and ('is_gif' not in reddit['data'] or not reddit['data']['is_gif']) \
                and ('is_gallery' not in reddit['data'] or not reddit['data']['is_gallery']):
            print("Selected a reddit from the list of reddits: {}".format(reddit))
            return reddit
    raise ValueError('Could not find a reddit with a title and picture from this list of reddits: {}'
                     .format(reddit_list))


if __name__ == '__main__':
    lambda_handler('Command line event', 'Command line context')
