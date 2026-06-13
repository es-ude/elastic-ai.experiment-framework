#include "msg_handler.h"
#include "frame_builder.h"
#include "sender.h"
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

int msg_open_task(Frame *frame, TaskManager *task_manager)
{
    Task *task = get_task_by_id(frame->header.transaction_id, task_manager);
    if (task == NULL || task->status != TASK_STATUS_IDLE)
    {
        printf("No free tasks available\n");
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
        printf("Invalid task ID in close task: %d\n", frame->header.transaction_id);
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
    printf("[Server] Handle incoming data chunk\n");
    Task *task = get_task_by_id(frame->header.transaction_id, task_manager); // Get the task ID from the first byte of the payload to identify which task this data chunk belongs to
    if (task == NULL || task->status == TASK_STATUS_IDLE)
    {
        printf("Invalid task ID in data chunk: %d\n", frame->header.transaction_id);
        return -1; // Invalid task ID
    }
    printf("[Server] Fetched Task with id %i\n", frame->header.transaction_id);

    send_frame_to_task(task_rb, task, frame);
    return task->id;
}

/*
 * Handles the frame interpreation.
 *  Return code:
 *          @param 0 no frame should be sent back
 *          @param 1 send the "response" frame
 *          @param 2 Connection Close Frame
 *          @param -1 error code
 */
void handle_incoming_frame(RingBuffer *task_rb, Frame *frame, TaskManager *task_manager)
{
    int associated_transaction_id = 0, result_code = 0;

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

        associated_transaction_id = msg_open_task(frame, task_manager);

        result_code = 0; // Send return frame back

        tx->msg_counter[frame->header.transaction_id] = 1; // reset msg_id of outgoing messages. 0 is open task, 1 is following
        break;
    case CLOSE_TASK:
        associated_transaction_id = msg_close_task(frame, task_manager);
        break;
    case RETURN:
        msg_return(frame);
        break;
    case DATA_CHUNK:
        printf("[Server] Handling DATA_CHUNK message\n");
        associated_transaction_id = msg_data_chunk(task_rb, frame, task_manager);

        break;
    case ACK:
        break;
    case NACK:
        break;
    case HANDSHAKE:

        break;

    default:
        printf("Unknown message type: %02X\n", frame->header.message_type);
        result_code = -2; // Unknown message type
        break;
    }
}