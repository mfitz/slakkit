import os
import pytest
import slack
from slack.errors import SlackApiError

import main


def test_propagates_errors_when_sending_slack_messages(mocker):
    slack_error = SlackApiError("OOOOOOOOPSY DAISY!", 'some-response')
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


def test_reads_slack_oauth_token_from_env_var_when_set_directly_as_env_var():
    token = "xoxb-some-oauth-token"
    os.environ["slakkit_OAUTH_TOKEN"] = token
    try:
        token = main.get_slack_oauth_token()

        assert token == token, "OAuth token not read from environmental variable"
    finally:
        del os.environ['slakkit_OAUTH_TOKEN']


def test_reads_slack_oauth_token_from_secrets_when_not_set_directly_as_env_var(mocker):
    mocker.patch.object(main, 'get_secret', return_value={"api_key": "some-key"})
    secret_name = "slakkit/slack-token"
    os.environ["slakkit_OAUTH_TOKEN"] = secret_name
    try:
        token = main.get_slack_oauth_token()

        assert token == "some-key", "OAuth token not read from secrets"
        main.get_secret.assert_called_once_with(secret_name)
    finally:
        del os.environ['slakkit_OAUTH_TOKEN']
