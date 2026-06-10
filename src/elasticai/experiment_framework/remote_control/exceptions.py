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
