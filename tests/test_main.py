import os

import pytest
import requests
import slack
from slack.errors import SlackApiError

import main


@pytest.fixture()
def subreddit_list():
    yield ['lions', 'tigers', 'bears']


@pytest.fixture()
def a_good_reddit_image_post():
    yield {
        "kind": "t3",
        "data": {
            "is_video": False,
            "subreddit": "CatsInBusinessAttire",
            "title": "A stray showed up next door with the snazziest striped tie.",
            "permalink": "https://www.reddit.com/r/CatsInBusinessAttire/comments/psoukm/dashing_neck_tie/",
            "post_hint": "image",
            "url_overridden_by_dest": "https://i.redd.it/am25oz0yafv71.jpg"
        }
    }


def test_propagates_errors_when_sending_slack_messages(mocker):
    slack_error = SlackApiError("OOPSY DAISY!", 'some-response')
    mocker.patch.object(slack.WebClient, 'chat_postMessage', side_effect=slack_error)

    with pytest.raises(SlackApiError) as raised_error:
        main.send_slack_message('some-channel', 'some-token', [])

    assert raised_error.value == slack_error, 'Error raised was not the one expected'


def test_prints_slack_api_response_when_sending_slack_messages(mocker):
    response = {"Stuff": "Some response stuff"}
    mocker.patch.object(slack.WebClient, 'chat_postMessage', return_value=response)
    mocker.patch.object(main, 'print')

    main.send_slack_message('some-channel', 'some-token', [])

    main.print.assert_any_call('Slack API response: {}'.format(response))


def test_reads_slack_oauth_token_when_set_directly_as_env_var():
    token = "xoxb-some-oauth-token"
    os.environ["slakkit_OAUTH_TOKEN"] = token
    try:
        assert main.get_slack_oauth_token() == token, "OAuth token not read from environmental variable"
    finally:
        del os.environ['slakkit_OAUTH_TOKEN']


def test_reads_slack_oauth_token_from_secrets_when_set_indirectly(mocker):
    token = "some-key"
    mocker.patch.object(main, 'get_secret', return_value={"api_key": token})
    secret_name = "slakkit/slack-token"
    os.environ["slakkit_OAUTH_TOKEN"] = secret_name
    try:
        assert main.get_slack_oauth_token() == token, "OAuth token not read from secrets"
        main.get_secret.assert_called_once_with(secret_name)
    finally:
        del os.environ['slakkit_OAUTH_TOKEN']


def test_slack_message_begins_with_reddit_title(a_good_reddit_image_post):
    message_blocks = main.make_slack_message_blocks(a_good_reddit_image_post)

    expected_title_section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "> {}".format(a_good_reddit_image_post['data']['title'])
        }
    }
    assert expected_title_section == message_blocks[0], "Slack message does not begin with the expected title section"


def test_reddit_image_follows_title_in_slack_message(a_good_reddit_image_post):
    message_blocks = main.make_slack_message_blocks(a_good_reddit_image_post)

    expected_image_section = {
        "type": "image",
        "image_url": "{}".format(a_good_reddit_image_post['data']['url_overridden_by_dest']),
        "alt_text": "image"
    }
    assert expected_image_section == message_blocks[1], "Slack message does not have the expected image section"


def test_reddit_hyperlink_follows_image_in_slack_message(a_good_reddit_image_post):
    message_blocks = main.make_slack_message_blocks(a_good_reddit_image_post)

    expected_link_section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Pulled from the <{}|{}> subreddit".format(
                'https://www.reddit.com{}'.format(a_good_reddit_image_post['data']['permalink']),
                a_good_reddit_image_post['data']['subreddit'])
        }
    }
    assert expected_link_section == message_blocks[2], "Slack message does not have the expected hyperlink section"


def test_slack_message_ends_with_divider(a_good_reddit_image_post):
    message_blocks = main.make_slack_message_blocks(a_good_reddit_image_post)

    expected_divider_section = {'type': 'divider'}
    assert expected_divider_section == message_blocks[-1], "Slack message does not end with a divider"


def test_reads_secrets_from_aws_as_dicts(mocker):
    mock_client = mocker.MagicMock()
    mock_client.get_secret_value.return_value = {"SecretString": '{"Thingy": "Whatsit"}'}
    mocker.patch.object(main.boto3, 'client', return_value=mock_client)

    assert main.get_secret("SomeSecret") == {"Thingy": "Whatsit"}


def test_throws_error_when_retrieved_secret_has_no_secret_string(mocker):
    mock_client = mocker.MagicMock()
    mock_client.get_secret_value.return_value = {"SecretBinary": b'{"Thingy": "Whatsit"}'}
    mocker.patch.object(main.boto3, 'client', return_value=mock_client)

    with pytest.raises(ValueError) as raised_error:
        main.get_secret("SomeSecret") == {"Thingy": "Whatsit"}

    assert raised_error.value.args[0] == "Did not find an appropriate secret under the name 'SomeSecret'"


def test_queries_reddit_api_for_top_subreddit_posts(mocker):
    mocker.patch.object(requests, 'get')
    mocker.patch.object(requests.get, 'json', return_value={"data": {"children": []}})

    main.get_top_posts('some-reddit', 50, 'month')

    requests.get.assert_called_once_with("https://www.reddit.com/r/some-reddit/top.json?limit=50&t=month",
                                         headers=mocker.ANY)


def test_sets_user_agent_header_when_querying_reddit_api(mocker):
    mocker.patch.object(requests, 'get')
    mocker.patch.object(requests.get, 'json', return_value={"data": {"children": []}})

    main.get_top_posts('some-reddit', 50, 'month')

    requests.get.assert_called_once_with(mocker.ANY, headers={'User-agent': 'Slakkit 0.1'})


def test_prints_reddit_api_responses(mocker):
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"kind": "listing", "data": {"children": []}}
    mocker.patch.object(requests, 'get', return_value=mock_response)
    mocker.patch.object(main, 'print')

    main.get_top_posts('some-reddit', 50, 'month')

    main.print.assert_any_call("Got response: {}".format(mock_response))


def test_extracts_posts_list_from_subreddit_api_responses(mocker):
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"kind": "listing", "data": {"children": []}}
    mocker.patch.object(requests, 'get', return_value=mock_response)
    mocker.patch.object(main, 'print')

    top_posts = main.get_top_posts('some-reddit', 50, 'month')

    assert top_posts == []
    mock_response.json.assert_called_once()


def test_randomly_chooses_subreddit_to_query(mocker, subreddit_list):
    chosen_subreddit = subreddit_list[-1]
    mocker.patch.object(main.random, 'choice', return_value=chosen_subreddit)
    mocker.patch.object(main, 'get_top_posts', return_value=[{}] * 50)

    main.get_random_reddits(subreddit_list)

    main.random.choice.assert_called_once_with(subreddit_list)
    main.get_top_posts.assert_called_once_with(chosen_subreddit, 50, 'month')


def test_overrides_default_reddit_api_page_size_with_optional_env_var(mocker, subreddit_list):
    mocker.patch.object(main, 'get_top_posts', return_value=[{}] * 50)
    os.environ["slakkit_REDDIT_PAGE_SIZE"] = '3'
    try:
        main.get_random_reddits(subreddit_list)

        main.get_top_posts.assert_called_once_with(mocker.ANY, 3, 'month')
    finally:
        del os.environ['slakkit_REDDIT_PAGE_SIZE']


def test_requests_more_data_when_reddit_returns_too_few_posts(mocker, subreddit_list):
    chosen_subreddit = subreddit_list[-1]
    mocker.patch.object(main.random, 'choice', return_value=chosen_subreddit)
    mocker.patch.object(main, 'get_top_posts', return_value=[{}])

    main.get_random_reddits(subreddit_list)

    main.get_top_posts.assert_has_calls([
        mocker.call(chosen_subreddit, 50, 'month'),
        mocker.call(chosen_subreddit, 50, 'year')
    ])


def test_raises_error_when_no_suitable_reddit_image_is_available():
    with pytest.raises(ValueError) as raised_error:
        main.choose_a_reddit([])
    assert raised_error.value.args[0] == 'Could not find a suitable image post from this list of reddits: []'


def test_shuffles_reddit_posts_before_choosing_one(mocker, a_good_reddit_image_post):
    posts = [a_good_reddit_image_post]
    mocker.patch.object(main.random, 'shuffle')

    main.choose_a_reddit(posts)

    main.random.shuffle.assert_called_once_with(posts)


def test_chooses_an_acceptable_image_post_when_available(a_good_reddit_image_post):
    chosen_post = main.choose_a_reddit([a_good_reddit_image_post])

    assert chosen_post == a_good_reddit_image_post


def test_ignores_image_posts_that_are_videos(a_good_reddit_image_post):
    video_post = a_good_reddit_image_post
    video_post['data']['is_video'] = True
    with pytest.raises(ValueError) as raised_error:
        main.choose_a_reddit([video_post])
    assert raised_error.value.args[0] == \
           'Could not find a suitable image post from this list of reddits: {}'.format([video_post])


def test_ignores_image_posts_that_are_galleries(a_good_reddit_image_post):
    gallery_post = a_good_reddit_image_post
    gallery_post['data']['is_gallery'] = True
    with pytest.raises(ValueError) as raised_error:
        main.choose_a_reddit([gallery_post])
    assert raised_error.value.args[0] == \
           'Could not find a suitable image post from this list of reddits: {}'.format([gallery_post])


def test_ignores_image_posts_that_are_gifs(a_good_reddit_image_post):
    gif_post = a_good_reddit_image_post
    gif_post['data']['is_gif'] = True
    with pytest.raises(ValueError) as raised_error:
        main.choose_a_reddit([gif_post])
    assert raised_error.value.args[0] == \
           'Could not find a suitable image post from this list of reddits: {}'.format([gif_post])
