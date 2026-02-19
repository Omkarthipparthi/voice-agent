"""
Telnyx telephony provider.
Parses Telnyx TeXML Media Stream WebSocket messages and generates TeXML.
"""

import json
from typing import Tuple
from . import TelephonyProvider


class TelnyxProvider(TelephonyProvider):

    @property
    def name(self) -> str:
        return "Telnyx"

    def parse_event(self, raw_message: str) -> Tuple[str, dict]:
        data = json.loads(raw_message)
        event = data.get("event", "")

        # Debug: log first message of each type to discover field names
        if event in ("connected", "start", "stop"):
            print(f"🔍 [Telnyx] event={event} payload={json.dumps(data, indent=2)}")

        if event == "start":
            # Telnyx may use "streamSid" or nested differently
            start_data = data.get("start", data)
            stream_sid = (
                start_data.get("streamSid")
                or start_data.get("stream_sid")
                or start_data.get("callSid")
                or start_data.get("call_sid")
                or start_data.get("streamId")
                or "unknown"
            )
            return "start", {"stream_sid": stream_sid}

        elif event == "media":
            return "media", {"payload": data["media"]["payload"]}

        elif event == "stop":
            return "stop", {}

        elif event == "mark":
            return "mark", {}

        return "ignore", {}

    def format_audio_response(self, stream_sid: str, base64_audio: str) -> str:
        return json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": base64_audio,
            },
        })

    def format_clear_message(self, stream_sid: str) -> str:
        return json.dumps({
            "event": "clear",
            "streamSid": stream_sid,
        })

    def format_mark_message(self, stream_sid: str, mark_name: str) -> str:
        return json.dumps({
            "event": "mark",
            "streamSid": stream_sid,
            "mark": {"name": mark_name},
        })

    def generate_call_response(self, host: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Say>Please wait while I connect you to the AI assistant.</Say>"
            "<Pause length=\"1\"/>"
            "<Say>Okay, you can start talking!</Say>"
            "<Connect>"
            f'<Stream url="wss://{host}/media-stream/telnyx"'
            ' track="inbound_track"'
            ' bidirectionalMode="rtp"'
            ' bidirectionalCodec="PCMU"'
            ' bidirectionalSamplingRate="8000"'
            "/>"
            "</Connect>"
            "</Response>"
        )
