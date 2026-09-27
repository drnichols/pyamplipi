"""Model parsing tests, using payloads shaped like what AmpliPi firmware actually sends."""

import copy
from datetime import datetime, timezone

import pytest
from pydantic import SecretStr

from pyamplipi.models import Alert, AlertLevel, BrowsableItemResponse, BrowserSelection, FirmwareInfo, Info, \
    PandoraRating, PlayItemResponse, SourceInfo, Status

ACCESS_KEY = 'super-secret-session-token'

# /api/info as sent by pre-0.4 firmware: none of the new fields
OLD_INFO = {
    'config_file': 'house.json',
    'version': '0.1.9',
    'mock_ctrl': False,
    'mock_streams': False,
}

# /api/info as sent by current firmware (upstream schema example, plus the real wire quirks)
NEW_INFO = {
    'config_file': 'house.json',
    'version': '0.4.9',
    'mock_ctrl': False,
    'mock_streams': False,
    'is_streamer': False,
    'online': True,
    'latest_release': '0.4.9',
    'access_key': ACCESS_KEY,
    'lms_mode': False,
    'serial': '212',
    'expanders': [112, 113],  # ctrl._update_serial() assigns the raw EEPROM ints
    'fw': [{'version': '1.6', 'git_hash': 'de0f8ec', 'git_dirty': False}],
    'stream_types_available': ['airplay', 'pandora', 'fileplayer'],
    'extra_fields': {'custom': 1},
    'connected_drives': ['/media/USBStick'],
    'global_alerts': [
        {'message': 'Disk nearly full', 'severity': 'warning', 'hidden': False,
         'timestamp': '2026-09-01T12:30:00+00:00'},
    ],
}

SOURCE_INFO = {
    'name': 'Pandora - pandora',
    'state': 'playing',
    'type': 'pandora',
    'artist': 'Cake',
    'track': 'Comanche',
    'album': 'Fashion Nugget',
    'station': 'Cake Radio',
    'img_url': 'https://example.com/art.jpg',
    'supported_cmds': ['play', 'pause', 'love', 'ban', 'shelve'],
    'rating': 1,
}


def status_payload(info):
    return {
        'sources': [{'id': 0, 'name': 'Input 1', 'input': 'stream=1005', 'info': SOURCE_INFO}],
        'zones': [], 'groups': [], 'streams': [], 'presets': [],
        'info': info,
    }


# -- Info: backwards compatibility

def test_info_parses_old_firmware_payload():
    info = Info.model_validate(OLD_INFO)
    assert info.version == '0.1.9'
    assert info.serial is None
    assert info.expanders == []
    assert info.global_alerts == []
    assert info.access_key is None


def test_info_version_is_not_required():
    info = Info.model_validate({})
    assert info.version == 'unknown'
    assert info.config_file == 'unknown'


def test_info_existing_defaults_match_upstream_semantics():
    info = Info.model_validate({'version': '0.1.9'})
    assert info.online is False
    assert info.latest_release is None
    assert info.fw == []


@pytest.mark.parametrize('field', ['online', 'latest_release'])
def test_info_accepts_null_for_existing_optional_fields(field):
    Info.model_validate({**OLD_INFO, field: None})


def test_info_null_fw_becomes_empty_list():
    assert Info.model_validate({**OLD_INFO, 'fw': None}).fw == []


def test_firmware_info_defaults_and_nulls():
    assert FirmwareInfo.model_validate({}) == FirmwareInfo(version='unknown', git_hash='unknown', git_dirty=False)
    FirmwareInfo.model_validate({'version': None, 'git_hash': None, 'git_dirty': None})


# -- Info: new fields

def test_info_parses_new_fields():
    info = Info.model_validate(NEW_INFO)
    assert info.serial == '212'
    assert info.stream_types_available == ['airplay', 'pandora', 'fileplayer']
    assert info.extra_fields == {'custom': 1}
    assert info.connected_drives == ['/media/USBStick']
    assert info.is_streamer is False
    assert info.lms_mode is False


def test_info_expanders_sent_as_ints_become_strings():
    assert Info.model_validate(NEW_INFO).expanders == ['112', '113']


@pytest.mark.parametrize('raw', ['None', '-1', '', False, None, -1])
def test_info_placeholder_serials_become_none(raw):
    assert Info.model_validate({**OLD_INFO, 'serial': raw}).serial is None


def test_info_integer_serial_becomes_string():
    assert Info.model_validate({**OLD_INFO, 'serial': 212}).serial == '212'


@pytest.mark.parametrize('field', ['expanders', 'stream_types_available', 'connected_drives', 'global_alerts'])
def test_info_null_lists_become_empty(field):
    assert getattr(Info.model_validate({**OLD_INFO, field: None}), field) == []


def test_info_global_alerts():
    alert = Info.model_validate(NEW_INFO).global_alerts[0]
    assert alert.message == 'Disk nearly full'
    assert alert.severity == AlertLevel.WARNING
    assert alert.hidden is False
    assert alert.timestamp == datetime(2026, 9, 1, 12, 30, tzinfo=timezone.utc)


def test_alert_defaults():
    alert = Alert.model_validate({'message': 'boom'})
    assert alert.severity == AlertLevel.ERROR
    assert alert.hidden is False
    assert alert.timestamp is None


def test_alert_unknown_severity_is_kept_not_rejected():
    assert Alert.model_validate({'message': 'boom', 'severity': 'critical'}).severity == 'critical'


# -- Info: access_key is a credential

def test_info_access_key_is_readable():
    assert Info.model_validate(NEW_INFO).access_key.get_secret_value() == ACCESS_KEY


def test_info_empty_access_key_becomes_none():
    assert Info.model_validate({**OLD_INFO, 'access_key': ''}).access_key is None


def test_info_access_key_not_leaked():
    info = Info.model_validate(NEW_INFO)
    assert ACCESS_KEY not in repr(info)
    assert ACCESS_KEY not in str(info)
    assert ACCESS_KEY not in info.model_dump_json()
    status = Status.model_validate(status_payload(NEW_INFO))
    assert ACCESS_KEY not in status.model_dump_json()


# -- SourceInfo

def test_source_info_parses_new_fields():
    info = SourceInfo.model_validate({**SOURCE_INFO, 'temporary': 'yes'})
    assert info.type == 'pandora'
    assert info.rating == PandoraRating.LIKED
    assert info.temporary == 'yes'


def test_source_info_new_fields_optional():
    info = SourceInfo.model_validate({'name': 'None', 'state': 'stopped'})
    assert info.type is None
    assert info.rating is None
    assert info.temporary is None


def test_source_info_unknown_rating_becomes_none():
    assert SourceInfo.model_validate({**SOURCE_INFO, 'rating': 9}).rating is None


def test_source_info_boolean_temporary_is_accepted():
    SourceInfo.model_validate({**SOURCE_INFO, 'temporary': True})


# -- Status

@pytest.mark.parametrize('info', [OLD_INFO, NEW_INFO])
def test_status_parses_with_and_without_new_fields(info):
    status = Status.model_validate(status_payload(info))
    assert status.info is not None
    assert status.sources[0].info.rating == PandoraRating.LIKED


def test_status_round_trips_through_dict():
    # micro-nova/hacs_amplipi's coordinator does resp.dict() -> Status(**state)
    status = Status.model_validate(status_payload(NEW_INFO))
    again = Status(**status.model_dump())
    assert again == status
    assert again.info.access_key.get_secret_value() == ACCESS_KEY


def test_status_payload_is_not_mutated():
    payload = status_payload(NEW_INFO)
    before = copy.deepcopy(payload)
    Status.model_validate(payload)
    assert payload == before


# -- browse / play models (upstream schema_extra examples)

def test_browsable_item_response():
    resp = BrowsableItemResponse.model_validate({'items': [
        {'id': '0', 'name': 'Blink-182 Radio', 'playable': True, 'parent': False},
        {'id': '/media/USBStick/Music', 'name': 'Music', 'playable': False, 'parent': True,
         'img': 'static/imgs/folder.png'},
    ]})
    assert [i.name for i in resp.items] == ['Blink-182 Radio', 'Music']
    assert resp.items[0].img is None
    assert resp.items[1].parent is True


def test_browser_selection_serialises_item():
    assert BrowserSelection(item='/media/USBStick/Music').model_dump() == {'item': '/media/USBStick/Music'}


def test_play_item_response():
    resp = PlayItemResponse.model_validate({'directory': '/media/7FA5-ECB4', 'status': status_payload(NEW_INFO)})
    assert resp.directory == '/media/7FA5-ECB4'
    assert isinstance(resp.status, Status)


def test_play_item_response_directory_optional():
    assert PlayItemResponse.model_validate({'status': status_payload(OLD_INFO)}).directory is None


def test_secretstr_type():
    assert isinstance(Info.model_validate(NEW_INFO).access_key, SecretStr)
