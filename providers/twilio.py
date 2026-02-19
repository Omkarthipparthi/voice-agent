"""
Twilio telephony provider.
Parses Twilio Media Stream WebSocket messages and generates TwiML.
"""

import json
from typing import Tuple
from . import TelephonyProvider


class TwilioProvider(TelephonyProvider):

    @property
    def name(self) -> str:
        return "Twilio"

    def parse_event(self, raw_message: str) -> Tuple[str, dict]:
        data = json.loads(raw_message)
        event = data.get("event", "")

        if event == "start":
            return "start", {"stream_sid": data["start"]["streamSid"]}

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
            f'<Stream url="wss://{host}/media-stream/twilio"/>'
            "</Connect>"
            "</Response>"
        )
