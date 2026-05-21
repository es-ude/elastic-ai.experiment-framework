#include "receiver.h"
#include "sender.h"
#include "msg_handler.h"

#include <stdlib.h>
#include <stddef.h>
#include <stdio.h>

bool frame_parser_feed(Receiver *p, uint8_t byte)
{
    switch (p->state)
    {
    case WAIT_START:
        if (byte == 0xAA)
        {
            p->frame.header.start_byte = byte;
            p->state = WAIT_TYPE;
        }
        break;

    case WAIT_TYPE:
        p->frame.header.message_type = byte;
        p->state = WAIT_FLAGS;
        break;

    case WAIT_FLAGS:
        p->frame.header.flags = byte;
        p->state = WAIT_TX_ID;
        break;

    case WAIT_TX_ID:
        p->frame.header.transaction_id = byte;
        p->state = WAIT_LEN_H;
        break;

    case WAIT_LEN_H:
        p->len_bytes[0] = byte;
        p->state = WAIT_LEN_L;
        break;

    case WAIT_LEN_L:
    {
        p->len_bytes[1] = byte;

        uint16_t len =
            ((uint16_t)p->len_bytes[0] << 8) |
            (uint16_t)p->len_bytes[1];

        p->frame.header.payload_len = len;

        if (len > MAX_PAYLOAD)
        {
            p->state = WAIT_START; // invalid frame
            break;
        }

        p->index = 0;
        p->state = WAIT_PAYLOAD;
        break;
    }

    case WAIT_PAYLOAD:
    {
        p->frame.payload[p->index++] = byte;

        if (p->index >= p->frame.header.payload_len)
        {
            return true; // FRAME COMPLETE
        }
        break;
    }
    }

    return false;
}

void receive_byte(Receiver *rx)
{
    uint8_t byte = rx->transport->recv_byte(rx->transport);
    ringbuffer_push(rx->incoming_rb, &byte);
}

// Receive one Byte
void RX_ISR(Receiver *rx)
{
    receive_byte(rx);
}

void process_rx(Receiver *rx)
{
    uint8_t byte;

    while (ringbuffer_pop(rx->incoming_rb, &byte))
    {
        if (frame_parser_feed(rx, byte))
        {
            Frame frame = rx->frame;

            handle_incoming_frame(rx->task_rb, &frame);

            rx->state = WAIT_START;
        }
    }
}
