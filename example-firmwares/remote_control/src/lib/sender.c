#include "sender.h"

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
        send_byte(tx, tx->frame.header.transaction_id);

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

void add_to_unacked(Sender *tx, Frame *frame)
{
    for (int i = 0; i < UNACKED_MSG_MAX_AMOUNT; i++)
    {
        if (!tx_trackers[i].used)
        {
            tx_trackers[i].used = 1;
            tx_trackers[i].seq = frame->header.transaction_id;
            tx_trackers[i].frame = *frame;
            tx_trackers[i].last_sent_ms = 0; // Set to current time in ms
            tx_trackers[i].retry_count = 0;
            tx_trackers[i].state = STATE_SENT;
            break;
        }
    }
}

void on_ack(uint8_t transaction_id)
{
    for (int i = 0; i < UNACKED_MSG_MAX_AMOUNT; i++)
    {
        if (tx_trackers[i].used && tx_trackers[i].seq == transaction_id)
        {
            tx_trackers[i].used = 0;
            break;
        }
    }
}

void on_nack(Sender *tx, uint8_t transaction_id)
{
    for (int i = 0; i < UNACKED_MSG_MAX_AMOUNT; i++)
    {
        if (tx_trackers[i].used && tx_trackers[i].seq == transaction_id)
        {
            // Handle NACK (e.g., retry sending the frame)
            TxTracker *entry = &tx_trackers[i];

            if (entry->retry_count < MAX_RETRY_COUNT) // Max retry count
            {
                entry->retry_count++;
                entry->last_sent_ms = 0;                         // Reset to current time in ms
                entry->state = STATE_SENT;                       // Mark for retry
                ringbuffer_push(tx->outgoing_rb, &entry->frame); // Re-queue the frame for sending
            }
            else
            {
                entry->state = STATE_FAILED;
                entry->used = 0;
            }
            return;
        }
    }
}

void process_tx(Sender *tx)
{
    tx->transport = tx->transport;

    if (tx->state == TX_IDLE)
    {
        Frame frame;

        if (ringbuffer_pop(tx->outgoing_rb, &frame))
        {
            if (frame.header.flags & FLAG_NEED_ACK)
            {
                add_to_unacked(tx, &frame);
            }
            tx_start(tx, &frame); // start the parsing of the frame and sending it out
        }
    }
    tx_process(tx);
}
