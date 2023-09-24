import pytest
from slack_app import event_message

class Mock:
  async def mock_say(t):
    return t
  async def mock_ack():
    return None


# No text
@pytest.mark.asyncio
async def test_event_message():
  mock_event = {
    "text": ''
  }
  res = await event_message(mock_event, Mock.mock_ack, Mock.mock_say)
  assert res is None

# With text
@pytest.mark.asyncio
async def test_event_message_text(mocker):
  say_spy = mocker.spy(Mock, 'mock_say')
  mock_event_w_text = {
    "text": 'Foobar'
  }
  res = await event_message(mock_event_w_text, Mock.mock_ack, Mock.mock_say)
  assert res is None
  say_spy.assert_called_once_with('Foobar')

# Handle error
@pytest.mark.asyncio
async def test_event_message_error(mocker):
  def badFn():
    pass

  say_spy = mocker.spy(Mock, 'mock_say')
  mock_event_w_text = {
    "text": 'Foobar'
  }
  res = await event_message(mock_event_w_text, badFn, Mock.mock_say)
  assert res is None
  say_spy.assert_called_once_with('An error occurred.')

