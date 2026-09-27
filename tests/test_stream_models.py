"""Tests for the Stream / StreamUpdate models against AmpliPi API payloads."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from pyamplipi.amplipi import AmpliPi, json_ser_kwargs
from pyamplipi.models import Config, Status, Stream, StreamUpdate

RCA_STREAM = {"id": 996, "name": "Input 1", "type": "rca", "index": 0, "browsable": False, "disabled": True}
STATUS = {"streams": [RCA_STREAM, {"id": 1000, "name": "Groove Salad", "type": "internetradio"}]}


class TestStream(unittest.TestCase):

    def test_disabled_is_kept(self):
        stream = Stream.model_validate(RCA_STREAM)
        self.assertIs(stream.disabled, True)
        self.assertEqual(stream.index, 0)
        self.assertIs(stream.browsable, False)
        self.assertIs(stream.model_dump()["disabled"], True)

    def test_disabled_is_kept_in_status(self):
        status = Status.model_validate(STATUS)
        self.assertIs(status.streams[0].disabled, True)
        self.assertIs(status.model_dump()["streams"][0]["disabled"], True)

    def test_missing_fields_still_parse(self):
        # older firmware doesn't send the newer stream fields
        stream = Stream.model_validate({"id": 1000, "name": "Groove Salad", "type": "internetradio"})
        self.assertIsNone(stream.disabled)
        self.assertIsNone(stream.index)

    def test_disabled_survives_config_serialisation(self):
        # load_config() sends the config with the same serialisation settings
        config = Config.model_validate(STATUS)
        sent = json.loads(config.model_dump_json(**json_ser_kwargs))
        self.assertIs(sent["streams"][0]["disabled"], True)
        self.assertNotIn("disabled", sent["streams"][1])


class TestStreamUpdate(unittest.TestCase):

    def test_disabled_is_serialised(self):
        self.assertEqual(StreamUpdate(disabled=True).model_dump(**json_ser_kwargs), {"disabled": True})

    def test_unset_fields_are_not_sent(self):
        self.assertEqual(StreamUpdate(name="Radio").model_dump(**json_ser_kwargs), {"name": "Radio"})


class TestSetStream(unittest.IsolatedAsyncioTestCase):

    async def test_set_stream_sends_disabled(self):
        amplipi = AmpliPi("http://amplipi.local/api", http_session=MagicMock())
        amplipi._client = AsyncMock()
        amplipi._client.patch.return_value = STATUS

        status = await amplipi.set_stream(996, StreamUpdate(disabled=True))

        path, body = amplipi._client.patch.call_args.args
        self.assertEqual(path, "streams/996")
        self.assertEqual(json.loads(body), {"disabled": True})
        self.assertIs(status.streams[0].disabled, True)


if __name__ == "__main__":
    unittest.main()
