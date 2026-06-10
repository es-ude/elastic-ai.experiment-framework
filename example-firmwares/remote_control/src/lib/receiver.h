#ifndef RECEIVER_H
#define RECEIVER_H

#include "frame.h"
#include "ringbuffer.h"
#include "task_manager.h"
#include "sender.h"

#include "transport.h"

#define FRAME_LITTLE_ENDIAN 1

#if FRAME_LITTLE_ENDIAN

#define PARSE_UINT16(low, high) \
    ((uint16_t)(low) | ((uint16_t)(high) << 8))

#else

#define PARSE_UINT16(low, high) \
    (((uint16_t)(high) << 8) | (uint16_t)(low))

#endif

typedef struct
{
    Transport *transport;
    enum
    {
        WAIT_START,
        WAIT_TYPE,
        WAIT_FLAGS,
        WAIT_TX_ID,
        WAIT_LEN_L,
        WAIT_LEN_H,
        WAIT_PAYLOAD
    } state;

    RingBuffer *incoming_rb;
    RingBuffer *task_rb;

    Frame frame;

    uint16_t index; // payload index
    uint8_t len_bytes[2];
} Receiver;

void process_rx(Receiver *rx, TaskManager *task_manager, Sender *tx);

#endif