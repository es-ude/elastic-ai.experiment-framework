#include "msg_handler.h"
#include "frame_builder.h"
#include "msg_types.h"
#include "log.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum AckType
{
    SEND_ACK,
    SEND_NACK,
};

void print_payload(uint8_t *payload, uint8_t payload_len)
{
    LOG("[Payload] ");
    for (int i = 0; i < payload_len; i++)
    {
        LOG("%02X ", payload[i]);
    }
    LOG("\n\n");
}

int msg_open_task(Frame *frame, TaskManager *task_manager)
{
    Task *task = get_task_by_id(frame->header.transaction_id, task_manager);
    if (task == NULL || task->status != TASK_STATUS_IDLE)
    {
        LOG("No free tasks available\n");
        return -1;
    }

    init_task(task, frame, task_manager);
    return task->id;
}

int msg_close_task(Frame *frame, TaskManager *task_manager)
{
    Task *task = get_task_by_id(frame->header.transaction_id, task_manager);
    if (task == NULL || task->status == TASK_STATUS_IDLE)
    {
        LOG("Invalid task ID in close task: %d\n", frame->header.transaction_id);
        return -1;
    }

    finish_task(task, task_manager);
    return task->id;
}

int msg_return(Frame *frame)
{
    return -1; // Not implemented yet
}

// Handle incoming data chunk for a task. This will append the new chunk to the existing input data for the task
int msg_data_chunk(RingBuffer *task_rb, Frame *frame, TaskManager *task_manager)
{
    LOG("[Server] Handle incoming data chunk\n");
    Task *task = get_task_by_id(frame->header.transaction_id, task_manager); // Get the task ID from the first byte of the payload to identify which task this data chunk belongs to
    if (task == NULL || task->status == TASK_STATUS_IDLE)
    {
        LOG("Invalid task ID in data chunk: %d\n", frame->header.transaction_id);
        return -1;
    }
    LOG("[Server] Fetched Task with id %i\n", frame->header.transaction_id);

    send_frame_to_task(task_rb, task, frame);
    return task->id;
}

void send_ack(Frame *frame, Sender *tx, enum AckType ack_type)
{
    LOG("[Receiver] ACK requested for transaction ID: 0x%02X\n", frame->header.transaction_id);

    uint8_t data_id = frame->header.message_type;
    if (frame->header.message_type == DATA_CHUNK)
    {
        data_id = frame->payload[0]; // For data chunks, the data ID is in the first byte of the payload
    }

    Frame ack_frame = {0};
    if (ack_type == SEND_ACK)
    {
        frame_builder_ack(&ack_frame, frame->header.transaction_id, data_id);
    }
    else
    {
        frame_builder_nack(&ack_frame, frame->header.transaction_id, data_id);
    }
    OutgoingOrder order = {
        .frame = ack_frame,
        .is_retransmit = 0};

    ringbuffer_push(tx->outgoing_rb, &order);
}

void handle_incoming_frame(RingBuffer *task_rb, Frame *frame, TaskManager *task_manager, Sender *tx)
{
    int associated_transaction_id = 0;
    enum AckType ack_type = SEND_ACK;

    bool need_ack = (frame->header.flags & FLAG_NEED_ACK) != 0;

    LOG("\n[Server] Received frame \n Control Byte: %02X, Type: %02X, Transaction ID: %02X, "
        "Payload Len: %d\n\n",
        frame->header.start_byte, frame->header.message_type,
        frame->header.transaction_id, frame->header.payload_len);

    // Check checksum
    if (frame->header.flags & FLAG_HAS_CRC)
    {
        uint8_t incoming_checksum = frame->payload[frame->header.payload_len];
        uint8_t expected_checksum = crc8((uint8_t *)frame, FRAME_OVERHEAD + frame->header.payload_len);
        if (incoming_checksum != expected_checksum)
        {
            if (need_ack)
            {
                ack_type = SEND_NACK;
                LOG("[Server] Received frame with invalid checksum. Sending NACK. Received: %02X, Expected: %02X\n", incoming_checksum, expected_checksum);
                send_ack(frame, tx, ack_type);
                return;
            }
            else
            {
                LOG("[Server] Received frame with invalid checksum, but no ACK requested. Ignoring frame. Received: %02X, Expected: %02X\n", incoming_checksum, expected_checksum);
            }

            return;
        }
    }

    switch (frame->header.message_type)
    {
    case OPEN_TASK:
        LOG("[Server] Handling OPEN_TASK message.\n");

        associated_transaction_id = msg_open_task(frame, task_manager);

        tx->msg_counter[frame->header.transaction_id] = 0; // reset msg_id of outgoing messages. 0 is open task, 1 is following
        if (associated_transaction_id < 0)
        {
            LOG("[Server] Failed to open task for transaction ID: 0x%02X\n", frame->header.transaction_id);
            ack_type = SEND_NACK;
        }

        tx->msg_counter[frame->header.transaction_id] = 0; // reset msg_id of outgoing messages. 0 is open task, 1 is following
        break;
    case CLOSE_TASK:
        associated_transaction_id = msg_close_task(frame, task_manager);
        if (associated_transaction_id < 0)
        {
            LOG("[Server] Failed to close task for transaction ID: 0x%02X\n", frame->header.transaction_id);
            ack_type = SEND_NACK;
        }
        break;
    case RETURN:
        msg_return(frame);
        break;
    case DATA_CHUNK:
        LOG("[Server] Handling DATA_CHUNK message\n");
        associated_transaction_id = msg_data_chunk(task_rb, frame, task_manager);

        if (associated_transaction_id < 0)
        {
            LOG("[Server] Failed to process data chunk for transaction ID: 0x%02X\n", frame->header.transaction_id);
            ack_type = SEND_NACK;
        }

        break;
    case ACK:
        on_ack(tx, frame->header.msg_id);
        break;
    case NACK:
        on_nack(tx, frame->header.msg_id);
        break;
    case HANDSHAKE:

        break;

    default:
        LOG("Unknown message type: %02X\n", frame->header.message_type);
        ack_type = SEND_NACK; // Unknown message type
        break;
    }

    if (need_ack)
    {
        send_ack(frame, tx, ack_type);
    }
}