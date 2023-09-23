import pytest
from slack_app import event_message

def mock_get(a, b):
  if b:
    return b
  else:
    return a

mock_event = {
  "get": mock_get
}
async def mock_ack():
  return None
async def mock_say(t):
  return await t

@pytest.mark.asyncio
async def test_event_message():
  res = await event_message(mock_event, mock_ack, mock_say)
  assert res is None