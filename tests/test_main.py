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
