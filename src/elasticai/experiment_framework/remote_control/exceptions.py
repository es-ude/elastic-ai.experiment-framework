from typing import TYPE_CHECKING

from .constants import NackErrorCode

if TYPE_CHECKING:
    from .message import Message


class ProtocolError(Exception):
    pass


class UnexpectedMessageError(ProtocolError):
    pass


class ReceivedNackError(ProtocolError):
    def __init__(self, error_code: NackErrorCode):
        self.error_code = error_code
        super().__init__("Received Nack")


class InvalidHeaderError(ProtocolError):
    pass


class DeviceAlreadyConnectedError(ProtocolError):
    pass


class DeviceNotFoundError(ProtocolError):
    pass


class InvalidTaskIdError(ValueError): ...


class InvalidMsgIdError(ValueError): ...


class InvalidPayloadLenError(ValueError): ...


class MessageRetransmissionError(ValueError): ...

class MessageDecodeError(ProtocolError):
    """Base class for errors encountered while decoding a wire message."""

    nack_code: NackErrorCode | None = None

    def __init__(self, reason: str, message: "Message | None" = None) -> None:
        self.message = message
        super().__init__(reason)


class InvalidCommandPayloadError(MessageDecodeError):
    nack_code = NackErrorCode.INVALID_PAYLOAD


class InvalidChecksumError(MessageDecodeError):
    nack_code = NackErrorCode.INVALID_CHECKSUM

    def __init__(self, message: "Message") -> None:
        super().__init__("Invalid checksum", message)
        

class MessageFramingError(MessageDecodeError):
    """Raised when a message could not be parsed; stream has been resynced."""
