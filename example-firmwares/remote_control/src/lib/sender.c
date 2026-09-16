#include "sender.h"
#include "frame_builder.h"
#include "log.h"

#include <stdio.h>

bool tx_start(Sender *tx, Frame *frame, uint8_t is_retransmitting)
{
    tx->frame = *frame; // copy header + pointer
    tx->index = 0;
    tx->state = TX_SEND_START;
    tx->is_retransmitting = is_retransmitting;
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

        if (tx->is_retransmitting)
        {
            send_byte(tx, tx->frame.header.msg_id); // msg_id already exists
        }
        else
        {
            uint8_t msg_id = tx->msg_counter[transaction_id];
            send_byte(tx, msg_id);
            tx->msg_counter[transaction_id]++;
        }

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

    OutgoingOrder order = {
        .frame = frame,
        .is_retransmit = 0};

    ringbuffer_push(task_s->outgoing_rb, &order);
}

uint8_t send_data(TaskServices *task_s, uint8_t flags, uint8_t *data, uint32_t data_len)
{
    Frame frame = {0};
    frame_builder_data_chunk(&frame, flags, data, data_len, task_s->task_id, 0, 0);

    OutgoingOrder order = {
        .frame = frame,
        .is_retransmit = 0};

    ringbuffer_push(task_s->outgoing_rb, &order);
}

bool add_to_unacked(Sender *tx, Frame *frame)
{
    for (int i = 0; i < UNACKED_MSG_MAX_AMOUNT; i++)
    {
        AckTracker *tracker = &(tx->ack_trackers[i]);
        if (!tracker->used)
        {
            tracker->used = 1;
            tracker->seq = frame->header.msg_id;
            tracker->frame = *frame;
            tracker->last_sent_ms = transport_get_current_time();
            tracker->retry_count = 0;
            tracker->state = STATE_SENT;
            return true;
        }
    }
    return false;
}

void on_ack(Sender *tx, uint8_t acked_msg_id)
{
    LOG("Received ACK for msg_id %d\n", acked_msg_id);
    for (int i = 0; i < UNACKED_MSG_MAX_AMOUNT; i++)
    {
        AckTracker *tracker = &(tx->ack_trackers[i]);
        if (tracker->used && tracker->seq == acked_msg_id)
        {
            LOG("Received ACK for msg_id %d\n", acked_msg_id);
            tracker->used = 0;
            break;
        }
    }
}

void on_nack(Sender *tx, uint8_t nacked_msg_id)
{
    for (int i = 0; i < UNACKED_MSG_MAX_AMOUNT; i++)
    {
        AckTracker *tracker = &(tx->ack_trackers[i]);
        if (tracker->used && tracker->seq == nacked_msg_id)
        {

            tracker->state = STATE_FAILED;
            tracker->used = 0;

            return;
        }
    }
}

void retransmit_unacked(Sender *tx, uint32_t current_time_s)
{
    for (int i = 0; i < UNACKED_MSG_MAX_AMOUNT; i++)
    {
        AckTracker *tracker = &tx->ack_trackers[i];

        if (!tracker->used)
            continue;

        if (tracker->state != STATE_SENT)
            continue;

        // printf("Retransmit check for msg_id %d, last_sent_ms: %d, current_time_ms: %d, retry_count: %d\n", tracker->seq, tracker->last_sent_ms, current_time_s, tracker->retry_count);

        if ((current_time_s - tracker->last_sent_ms) >= ACK_TIMEOUT_S)
        {
            // printf("Retransmitting unacked message with msg_id %d, retry_count: %d\n", tracker->seq, tracker->retry_count);

            if (tracker->retry_count < MAX_RETRY_COUNT)
            {
                tracker->retry_count++;
                tracker->last_sent_ms = current_time_s;

                OutgoingOrder order = {
                    .frame = tracker->frame,
                    .is_retransmit = 1};

                ringbuffer_push(tx->outgoing_rb, &order);
            }
            else
            {
                tracker->state = STATE_FAILED;
                tracker->used = 0;
            }
        }
    }
}

void process_tx(Sender *tx)
{
    tx->transport = tx->transport;

    retransmit_unacked(tx, transport_get_current_time());

    if (tx->state == TX_IDLE)
    {
        OutgoingOrder order = {0};

        if (ringbuffer_pop(tx->outgoing_rb, &order))
        {
            if (order.frame.header.flags & FLAG_NEED_ACK && !order.is_retransmit)
            {
                add_to_unacked(tx, &order.frame);
            }
            tx_start(tx, &order.frame, order.is_retransmit); // start the parsing of the frame and sending it out
        }
    }
    tx_process(tx);
}
