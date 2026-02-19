"""
Base telephony provider interface.
Defines the contract that Twilio, Telnyx, and any future provider must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class TelephonyProvider(ABC):
    """Abstract base class for telephony providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @abstractmethod
    def parse_event(self, raw_message: str) -> Tuple[str, dict]:
        """
        Parse a raw WebSocket message into a normalized event.

        Returns:
            (event_type, data) where event_type is one of:
            - "start"  → call started, data has "stream_sid"
            - "media"  → audio chunk, data has "payload" (base64)
            - "stop"   → call ended
            - "ignore" → unrecognized event, skip it
        """
        ...

    @abstractmethod
    def format_audio_response(self, stream_sid: str, base64_audio: str) -> str:
        """
        Format a base64-encoded audio chunk into the provider's
        WebSocket media message (as a JSON string).
        """
        ...

    @abstractmethod
    def format_clear_message(self, stream_sid: str) -> str:
        """
        Format a 'clear' message that flushes the provider's
        audio playback buffer (used for barge-in interruption).
        """
        ...

    @abstractmethod
    def format_mark_message(self, stream_sid: str, mark_name: str) -> str:
        """
        Format a 'mark' message. The provider will send back a 'mark' event
        when all audio queued before this mark has finished playing.
        """
        ...

    @abstractmethod
    def generate_call_response(self, host: str) -> str:
        """
        Generate the XML response for an incoming call webhook
        that connects the call to the media stream WebSocket.

        Args:
            host: The server hostname (for constructing the WSS URL)

        Returns:
            XML string (TwiML or TeXML)
        """
        ...
