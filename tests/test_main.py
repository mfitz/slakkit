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
    mocker.patch.object(slack.WebClient, 'chat_postMessage', return_value='{"Some response stuff"}')
    mocker.patch.object(main, 'print')

    main.send_slack_message('some-channel', 'some-token', [])

    main.print.assert_any_call('Slack API response: {"Some response stuff"}')

