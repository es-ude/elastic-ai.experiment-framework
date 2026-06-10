#include "msg_handler.h"
#include "task_manager.h"
#include "frame_builder.h"
#include "msg_types.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void print_payload(uint8_t *payload, uint8_t payload_len)
{
    printf("[Payload] ");
    for (int i = 0; i < payload_len; i++)
    {
        printf("%02X ", payload[i]);
    }
    printf("\n\n");
}

int msg_open_task(Frame *frame)
{
    Task *task = get_task_by_id(frame->header.transaction_id);
    if (task == NULL)
    {
        printf("No free tasks available\n");
        return -1;
    }

    init_task(task, frame);
    return task->id;
}

int msg_close_task(Frame *frame)
{
    Task *task = get_task_by_id(frame->header.transaction_id);
    if (task == NULL)
    {
        printf("Invalid task ID in close task: %d\n", frame->header.transaction_id);
        return -1;
    }

    finish_task(task);
    return task->id;
}

int msg_return(Frame *frame)
{
    return -1; // Not implemented yet
}

// Handle incoming data chunk for a task. This will append the new chunk to the existing input data for the task
int msg_data_chunk(RingBuffer *task_rb, Frame *frame)
{
    printf("[Server] Handle incoming data chunk\n");
    Task *task = get_task_by_id(frame->header.transaction_id); // Get the task ID from the first byte of the payload to identify which task this data chunk belongs to
    if (task == NULL || task->status == TASK_STATUS_IDLE)
    {
        printf("Invalid task ID in data chunk: %d\n", frame->header.transaction_id);
        return -1; // Invalid task ID. send back ack
    }
    printf("[Server] Fetched Task with id %i\n", frame->header.transaction_id);

    send_frame_to_task(task_rb, task, frame);
    return task->id;
}

void handle_incoming_frame(RingBuffer *task_rb, Frame *frame, Sender *tx)
{
    int associated_transaction_id = 0;
    enum
    {
        SEND_ACK,
        SEND_NACK,
    } ack_type = SEND_ACK;

    bool need_ack = (frame->header.flags & FLAG_NEED_ACK) != 0;

    printf("\n[Server] Received frame \n Control Byte: %02X, Type: %02X, Transaction ID: %02X, "
           "Payload Len: %d\n\n",
           frame->header.start_byte, frame->header.message_type,
           frame->header.transaction_id, frame->header.payload_len);
    print_payload(frame->payload, frame->header.payload_len);
    fflush(stdout);

    // Call differenet message handler
    switch (frame->header.message_type)
    {
    case OPEN_TASK:
        printf("[Server] Handling OPEN_TASK message.\n");

        associated_transaction_id = msg_open_task(frame);

        if (associated_transaction_id < 0)
        {
            printf("[Server] Failed to open task for transaction ID: 0x%02X\n", frame->header.transaction_id);
            ack_type = SEND_NACK; // Send nack back
        }

        break;
    case CLOSE_TASK:
        associated_transaction_id = msg_close_task(frame);
        if (associated_transaction_id < 0)
        {
            printf("[Server] Failed to close task for transaction ID: 0x%02X\n", frame->header.transaction_id);
            ack_type = SEND_NACK; // Send nack back
        }
        break;
    case RETURN:
        msg_return(frame);
        break;
    case DATA_CHUNK:
        printf("[Server] Handling DATA_CHUNK message\n");
        associated_transaction_id = msg_data_chunk(task_rb, frame);

        if (associated_transaction_id < 0)
        {
            printf("[Server] Failed to process data chunk for transaction ID: 0x%02X\n", frame->header.transaction_id);
            ack_type = SEND_NACK; // Send nack back
        }
        break;
    case ACK:
        on_ack(frame->header.transaction_id);
        break;
    case NACK:
        on_nack(tx, frame->header.transaction_id);
        break;
    case HANDSHAKE:

        break;

    default:
        printf("Unknown message type: %02X\n", frame->header.message_type);
        ack_type = SEND_NACK; // Unknown message type
        break;
    }

    if (need_ack)
    {
        printf("[Receiver] ACK requested for transaction ID: 0x%02X\n", frame->header.transaction_id);

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
        ringbuffer_push(tx->outgoing_rb, &ack_frame);
    }
}