#ifndef SENDER_H
#define SENDER_H

#include "frame.h"
#include "ringbuffer.h"

#include "transport.h"

typedef struct
{
    Transport *transport;
    enum
    {
        TX_IDLE,
        TX_SEND_START,
        TX_SEND_HEADER,
        TX_SEND_PAYLOAD,
        TX_DONE
    } state;

    RingBuffer *outgoing_rb;

    Frame frame;
    uint16_t index;

} Sender;

void tx_process(Sender *tx);
void process_tx(Sender *tx);

#endif