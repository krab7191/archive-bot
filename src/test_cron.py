import pytest
import asyncio

from cron import cron, init_cron

# @pytest.mark.asyncio
# async def test_cron():
#   res = await cron()
#   assert res == 'foo'


def test_init_cron(mocker):
    mocker.patch('asyncio.get_event_loop')
    res = init_cron()
    assert res is None
