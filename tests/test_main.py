import os
import pytest
import slack
from slack.errors import SlackApiError

import main


@pytest.fixture()
def some_reddit():
    yield {
        "data": {
            "title": "Dashing neck tie",
            "subreddit": "CatsInBusinessAttire",
            "permalink": "https://www.reddit.com/r/CatsInBusinessAttire/comments/psoukm/dashing_neck_tie/",
            "url_overridden_by_dest": "https://i.imgur.com/NCF8foo.jpg"
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


def test_slack_message_begins_with_reddit_title(some_reddit):
    message_blocks = main.make_slack_message_blocks(some_reddit)

    expected_title_section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "> {}".format(some_reddit['data']['title'])
        }
    }
    assert expected_title_section == message_blocks[0], "Slack message does not begin with the expected title section"


def test_reddit_image_link_follows_title_in_slack_message(some_reddit):
    message_blocks = main.make_slack_message_blocks(some_reddit)

    expected_image_section = {
        "type": "image",
        "image_url": "{}".format(some_reddit['data']['url_overridden_by_dest']),
        "alt_text": "image"
    }
    assert expected_image_section == message_blocks[1], "Slack message does not have the expected image section"


def test_reddit_hyperlink_follows_image_in_slack_message(some_reddit):
    message_blocks = main.make_slack_message_blocks(some_reddit)

    expected_link_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Pulled from the <{}|{}> subreddit".format(
                    'https://www.reddit.com{}'.format(some_reddit['data']['permalink']),
                    some_reddit['data']['subreddit'])
            }
        }
    assert expected_link_section == message_blocks[2], "Slack message does not have the expected hyperlink section"


def test_slack_message_ends_with_divider(some_reddit):
    message_blocks = main.make_slack_message_blocks(some_reddit)

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
