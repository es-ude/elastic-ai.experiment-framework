#ifndef ENUMS_H
#define ENUMS_H

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

enum TaskStatus
{
    TASK_STATUS_IDLE = 0,
    TASK_STATUS_PREPARING = 1,
    TASK_STATUS_RUNNING = 2

};

enum StreamStatus
{
    STREAM_STATUS_CLOSED = 0,
    STREAM_STATUS_OPEN = 1
};

enum StreamDirection
{
    STREAM_DIRECTION_INCOMING = 0,
    STREAM_DIRECTION_OUTGOING = 1
};

#endif