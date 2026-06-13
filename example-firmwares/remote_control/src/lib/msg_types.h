#pragma once

enum MessageType
{
    OPEN_TASK = 0x01,
    CLOSE_TASK = 0x02,
    RETURN = 0x03,
    DATA_CHUNK = 0x04,
    ACK = 0x05,
    NACK = 0x06,
    HANDSHAKE = 0x07
};