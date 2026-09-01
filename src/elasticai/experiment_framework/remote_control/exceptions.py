class ProtocolError(Exception):
    pass


class UnexpectedMessageError(ProtocolError):
    pass


class ReceivedNackError(ProtocolError):
    pass


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


class InvalidChecksumError(ValueError):
    def __init__(self, message: "Message"):  # type: ignore # noqa: F821
        self.message = message
        super().__init__("Invalid checksum")
        
class MessageFramingError(Exception):
    """Raised when a message could not be parsed; stream has been resynced."""
