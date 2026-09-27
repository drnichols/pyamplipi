"""AmpliPi Data Models - Extracted from the amplipi repo.
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import BaseModel, BeforeValidator, Field, SecretStr, field_validator

# AmpliPi is built on pydantic v1, which does not validate on assignment, so what it sends
# can differ from its declared types. These validators accept what the firmware actually
# sends, because a single field failing validation makes get_status() fail as a whole.


def _none_to_empty_list(value: Any) -> Any:
    return [] if value is None else value


def _int_to_str(value: Any) -> Any:
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else value


EmptyIfNone = BeforeValidator(_none_to_empty_list)


class PandoraRating(IntEnum):
    """ Pandora rating of the current track """
    DEFAULT = 0
    LIKED = 1  # "loved"
    DISLIKED = 2  # "banned"
    SHELVED = 3  # "tired"


class SourceInfo(BaseModel):
    """ Info about the current audio playing from the connected stream (generated during playback) """
    name: Optional[str] = None
    state: Optional[str] = None  # paused, playing, stopped, ???
    type: Optional[str] = None  # stream type of the playing source
    artist: Optional[str] = None
    track: Optional[str] = None
    album: Optional[str] = None
    station: Optional[str] = None  # name of radio station
    img_url: Optional[str] = None
    supported_cmds: List[str] = []
    rating: Optional[PandoraRating] = None  # only used for pandora
    temporary: Optional[Union[str, bool]] = None  # only used for file players

    @field_validator('rating', mode='before')
    @classmethod
    def _unknown_rating_to_none(cls, value: Any) -> Any:
        """ A rating added by newer firmware is dropped rather than failing the whole status """
        try:
            return None if value is None else PandoraRating(value)
        except (ValueError, TypeError):
            return None


class Source(BaseModel):
    """ An audio source """
    id: Optional[int] = None
    name: str
    input: str
    # Additional info about the current audio playing from the stream (generated during
    info: Optional[SourceInfo] = None
    # playback')


class SourceUpdate(BaseModel):
    """ Partial reconfiguration of an audio Source """
    name: Optional[str] = None
    input: Optional[str] = None  # 'None', 'local', 'stream=ID'


class SourceUpdateWithId(SourceUpdate):
    """ Partial reconfiguration of a specific audio Source """
    id: int


class Zone(BaseModel):
    """ Audio output to a stereo pair of speakers, typically belonging to a room """
    id: Optional[int] = None
    name: str
    source_id: int
    mute: bool
    vol: int
    vol_f: float
    vol_min: int
    vol_max: int
    disabled: bool


class ZoneUpdate(BaseModel):
    """ Reconfiguration of a Zone """
    name: Optional[str] = None
    source_id: Optional[int] = None
    mute: Optional[bool] = None
    vol: Optional[int] = None
    vol_f: Optional[float] = None
    vol_min: Optional[int] = None
    vol_max: Optional[int] = None
    disabled: Optional[bool] = None


class ZoneUpdateWithId(ZoneUpdate):
    """ Reconfiguration of a specific Zone """
    id: int


class MultiZoneUpdate(BaseModel):
    """ Reconfiguration of multiple zones specified by zone_ids and group_ids """
    zones: Optional[List[int]] = None
    groups: Optional[List[int]] = None
    update: ZoneUpdate


class Group(BaseModel):
    """ A group of zones that can share the same audio input and be controlled as a group ie. Upstairs. Volume, mute,
    and source_id fields are aggregates of the member zones."""
    id: Optional[int] = None
    name: str
    source_id: Optional[int] = None
    zones: List[int]
    mute: Optional[bool] = None
    vol_delta: Optional[int] = None
    vol_f: Optional[float] = None


class GroupUpdate(BaseModel):
    """ Reconfiguration of a Group """
    name: Optional[str] = None
    source_id: Optional[int] = None
    zones: Optional[List[int]] = None
    mute: Optional[bool] = None
    vol_delta: Optional[int] = None
    vol_f: Optional[float] = None


class GroupUpdateWithId(GroupUpdate):
    """ Reconfiguration of a specific Group """
    id: int


class Stream(BaseModel):
    """ Digital stream such as Pandora, AirPlay or Spotify """
    id: Optional[int] = None
    name: str
    type: str
    user: Optional[str] = None
    password: Optional[str] = None
    station: Optional[str] = None
    url: Optional[str] = None
    logo: Optional[str] = None
    freq: Optional[str] = None
    client_id: Optional[str] = None
    token: Optional[str] = None


class StreamUpdate(BaseModel):
    """ Reconfiguration of a Stream """
    name: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    station: Optional[str] = None
    url: Optional[str] = None
    logo: Optional[str] = None
    freq: Optional[str] = None


class BrowsableItem(BaseModel):
    """ An item that can be browsed on a browsable stream (Pandora, media device) """
    id: str  # unique within its stream
    name: str
    playable: bool
    parent: bool  # has browsable children
    img: Optional[str] = None


class BrowsableItemResponse(BaseModel):
    items: List[BrowsableItem]


class BrowserSelection(BaseModel):
    """ An item to browse into or play, e.g. '/media/USBStick/Music' """
    item: str


class StreamCommand(str, Enum):
    PLAY = 'play'
    PAUSE = 'pause'
    NEXT = 'next'
    PREV = 'prev'
    STOP = 'stop'
    LOVE = 'love'
    BAN = 'ban'
    SHELVE = 'shelve'


class PresetState(BaseModel):
    """ A set of partial configuration changes to make to sources, zones, and groups """
    sources: Optional[List[SourceUpdateWithId]] = None
    zones: Optional[List[ZoneUpdateWithId]] = None
    groups: Optional[List[GroupUpdateWithId]] = None


class Command(BaseModel):
    """ A command to execute on a stream """
    stream_id: int
    cmd: str


class Preset(BaseModel):
    id: Optional[int] = None
    name: str
    state: Optional[PresetState] = None
    commands: Optional[List[Command]] = None
    last_used: Union[int, None] = None


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[PresetState] = None
    commands: Optional[List[Command]] = None


class Announcement(BaseModel):
    media: str
    vol: Optional[int] = None
    vol_f: Optional[float] = None
    source_id: Optional[int] = None
    zones: Optional[List[int]] = None
    groups: Optional[List[int]] = None


class PlayMedia(BaseModel):
    media: str
    vol: Optional[int] = None
    vol_f: Optional[float] = None
    source_id: Optional[int] = None


class FirmwareInfo(BaseModel):
    version: Optional[str] = 'unknown'
    git_hash: Optional[str] = 'unknown'
    git_dirty: Optional[bool] = False


class AlertLevel(str, Enum):
    WARNING = 'warning'
    ERROR = 'error'
    INFO = 'info'
    SUCCESS = 'success'


class Alert(BaseModel):
    """ An alert shown to all users in the AmpliPi web app """
    message: str
    # a severity added by newer firmware is kept as a plain string rather than rejected
    severity: Union[AlertLevel, str] = Field(default=AlertLevel.ERROR, union_mode='left_to_right')
    hidden: bool = False
    timestamp: Optional[datetime] = None


class Info(BaseModel):
    config_file: str = 'unknown'
    version: str = 'unknown'
    mock_ctrl: bool = False
    mock_streams: bool = False
    is_streamer: bool = False
    online: Optional[bool] = False
    latest_release: Optional[str] = None
    access_key: Optional[SecretStr] = None  # credential: masked in repr() and JSON dumps
    lms_mode: bool = False
    serial: Optional[str] = None
    expanders: Annotated[List[Annotated[str, BeforeValidator(_int_to_str)]], EmptyIfNone] = []  # serial numbers
    fw: Annotated[List[FirmwareInfo], EmptyIfNone] = []
    stream_types_available: Annotated[List[str], EmptyIfNone] = []
    extra_fields: Optional[Dict[str, Any]] = None
    connected_drives: Annotated[List[str], EmptyIfNone] = []
    global_alerts: Annotated[List[Alert], EmptyIfNone] = []

    @field_validator('access_key', mode='before')
    @classmethod
    def _empty_access_key_to_none(cls, value: Any) -> Any:
        return None if value == '' else value

    @field_validator('serial', mode='before')
    @classmethod
    def _placeholder_serial_to_none(cls, value: Any) -> Any:
        """ AmpliPi sends str(serial), so 'None' (not read yet) and '-1' (no EEPROM) mean no serial """
        if value in (None, False, '', 'None', 'False', '-1', -1):
            return None
        return _int_to_str(value)


class Config(BaseModel):
    sources: List[Source] = []
    zones: List[Zone] = []
    groups: List[Group] = []
    streams: List[Stream] = []
    presets: List[Preset] = []


class Status(Config):
    info: Optional[Info] = None


class PlayItemResponse(BaseModel):
    directory: Optional[str] = None  # directory the stream's browser is now in
    status: Status


class AppSettings(BaseModel):
    mock_ctrl: bool = True
    mock_streams: bool = True
    config_file: str = 'house.json'
    delay_saves: bool = True
