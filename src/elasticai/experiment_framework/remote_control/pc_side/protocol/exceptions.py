class ProtocolError(Exception):
    pass


class UnexpectedMessageError(ProtocolError):
    pass


class InvalidHeaderError(ProtocolError):
    pass

class DeviceAlreadyConnectedError(ProtocolError): 
    pass


class DeviceNotFoundError(ProtocolError): 
    pass


class MaxDevicesReachedError(ProtocolError): 
    pass

