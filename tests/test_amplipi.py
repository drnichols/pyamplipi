"""AmpliPi method tests: check URL, verb and body of each call against a mocked HTTP client."""

import json
from unittest.mock import AsyncMock

import pytest

from pyamplipi.amplipi import AmpliPi
from pyamplipi.models import BrowsableItem, PlayItemResponse, Status

BROWSE_RESPONSE = {'items': [
    {'id': '0', 'name': 'Blink-182 Radio', 'playable': True, 'parent': False},
    {'id': '1', 'name': 'Cake Radio', 'playable': True, 'parent': False},
]}

STATUS = {'sources': [], 'zones': [], 'groups': [], 'streams': [], 'presets': [], 'info': {'version': '0.4.9'}}


@pytest.fixture
async def amplipi():
    api = AmpliPi('http://amplipi.local')
    api._client.get = AsyncMock()
    api._client.post = AsyncMock()
    yield api
    await api.close()


async def test_browse_stream_root_posts_without_body(amplipi):
    amplipi._client.post.return_value = BROWSE_RESPONSE

    items = await amplipi.browse_stream(1000)

    amplipi._client.post.assert_awaited_once_with('streams/browser/1000/browse', None)
    assert items == [BrowsableItem(**i) for i in BROWSE_RESPONSE['items']]


async def test_browse_stream_item_posts_selection(amplipi):
    amplipi._client.post.return_value = BROWSE_RESPONSE

    await amplipi.browse_stream(1000, '/media/USBStick/Music')

    path, body = amplipi._client.post.await_args.args
    assert path == 'streams/browser/1000/browse'
    assert json.loads(body) == {'item': '/media/USBStick/Music'}


async def test_browse_stream_child_gets(amplipi):
    amplipi._client.get.return_value = BROWSE_RESPONSE

    items = await amplipi.browse_stream_child(1000, 3)

    amplipi._client.get.assert_awaited_once_with('streams/1000/3/browse')
    assert [i.name for i in items] == ['Blink-182 Radio', 'Cake Radio']


async def test_browse_stream_child_rejects_negative_parent(amplipi):
    with pytest.raises(ValueError):
        await amplipi.browse_stream_child(1000, -1)
    amplipi._client.get.assert_not_awaited()


async def test_play_browsed_item_posts_selection(amplipi):
    amplipi._client.post.return_value = {'directory': '/media/USBStick', 'status': STATUS}

    resp = await amplipi.play_browsed_item(1000, '/media/USBStick/song.mp3')

    path, body = amplipi._client.post.await_args.args
    assert path == 'streams/browser/1000/play'
    assert json.loads(body) == {'item': '/media/USBStick/song.mp3'}
    assert isinstance(resp, PlayItemResponse)
    assert resp.directory == '/media/USBStick'
    assert isinstance(resp.status, Status)
