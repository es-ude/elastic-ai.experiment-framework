#include "sender.h"
#include "frame_builder.h"

#include <stdio.h>

bool tx_start(Sender *tx, Frame *frame)
{
    tx->frame = *frame; // copy header + pointer
    tx->index = 0;
    tx->state = TX_SEND_START;
    return true;
}

static void send_byte(Sender *tx, uint8_t b)
{
    tx->transport->send_byte(tx->transport, b);
}

void tx_process(Sender *tx)
{
    switch (tx->state)
    {
    case TX_IDLE:
        break;

    case TX_SEND_START:
        send_byte(tx, 0xAA);
        tx->state = TX_SEND_HEADER;
        break;

    case TX_SEND_HEADER:
        send_byte(tx, tx->frame.header.message_type);
        send_byte(tx, tx->frame.header.flags);
        uint8_t transaction_id = tx->frame.header.transaction_id;
        send_byte(tx, transaction_id);
        uint8_t msg_id = tx->msg_counter[transaction_id];
        send_byte(tx, msg_id);
        tx->msg_counter[transaction_id]++;

        send_byte(tx, tx->frame.header.payload_len & 0xFF);
        send_byte(tx, (tx->frame.header.payload_len >> 8) & 0xFF);

        tx->state = TX_SEND_PAYLOAD;
        tx->index = 0;
        break;

    case TX_SEND_PAYLOAD:
        if (tx->index < tx->frame.header.payload_len)
        {
            send_byte(tx, tx->frame.payload[tx->index++]);
        }
        else
        {
            tx->state = TX_DONE;
        }
        break;

    case TX_DONE:
        tx->state = TX_IDLE;
        break;
    }
}

uint8_t send_return(TaskServices *task_s, uint8_t flags, uint32_t return_code)
{
    Frame frame = {0};
    frame_builder_return(&frame, flags, return_code, task_s->task_id);
    ringbuffer_push(task_s->outgoing_rb, &frame);
}

uint8_t send_data(TaskServices *task_s, uint8_t flags, uint8_t *data, uint32_t data_len)
{
    Frame frame = {0};
    frame_builder_data_chunk(&frame, flags, data, data_len, task_s->task_id, 0, 0);
    ringbuffer_push(task_s->outgoing_rb, &frame);
}

void process_tx(Sender *tx)
{
    tx->transport = tx->transport;

    if (tx->state == TX_IDLE)
    {
        Frame frame;

        if (ringbuffer_pop(tx->outgoing_rb, &frame))
        {
            tx_start(tx, &frame);
        }
    }

    tx_process(tx);
}
