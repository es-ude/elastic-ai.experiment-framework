#ifndef RECEIVER_H
#define RECEIVER_H

#include "frame.h"
#include "ringbuffer.h"

#include "transport.h"

typedef struct
{
    Transport *transport;
    enum
    {
        WAIT_START,
        WAIT_TYPE,
        WAIT_FLAGS,
        WAIT_TX_ID,
        WAIT_LEN_H,
        WAIT_LEN_L,
        WAIT_PAYLOAD
    } state;

    RingBuffer *incoming_rb;
    RingBuffer *task_rb;

    Frame frame;

    uint16_t index; // payload index
    uint8_t len_bytes[2];
} Receiver;

Frame read_frame(int socket);

void process_rx(Receiver *rx);

#endif