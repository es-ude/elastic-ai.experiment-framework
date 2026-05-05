#include "msg_handler.h"
#include "task_manager.h"
#include "enums.h"
#include "frame_builder.h"
#include "task_manager.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int msg_open_task(Frame *frame, Server server)
{
    Task *task = get_free_task(); // Get a free Task prototype
    if (task == NULL)
    {
        printf("No free tasks available\n");
        return -1;
    }
    task->init(task, frame, server.server_fd, server.client_fd);
    return task->task_id;
}

int msg_close_task(Frame *frame)
{
    return -1; // Not implemented yet
}

int msg_return(Frame *frame)
{
    return -1; // Not implemented yet
}

// Handle incoming data chunk for a task. This will append the new chunk to the existing input data for the task
int msg_data_chunk(Frame *frame)
{
    DataChunkPayload *p = (DataChunkPayload *)frame->payload;

    printf("[Server] Handle incoming data chunk\n");
    Task *task = get_task_by_id(frame->header.transaction_id); // Get the task ID from the first byte of the payload to identify which task this data chunk belongs to
    if (task == NULL)
    {
        printf("Invalid task ID in data chunk: %d\n", frame->header.transaction_id);
        return -1; // Invalid task ID
    }
    printf("[Server] Fetched Task with id %i\n", frame->header.transaction_id);

    task->receive_datachunk(task, frame);

    return task->task_id;
}

/*
 * Handles the frame interpreation.
 *  Return code:
 *          @param 0 no frame should be sent back
 *          @param 1 send the "response" frame
 *          @param 2 Connection Close Frame
 *          @param -1 error code
 */
int handle_incoming_frame(Frame *frame, Server server, Frame *response)
{
    int associated_transaction_id;

    printf("\n[Server] Received frame \n Control Byte: %02X, Type: %02X, Start_Task_Flag: %i, Msg ID: %02X, "
           "Payload Len: %d\n\n",
           frame->header.start_byte, frame->header.message_type, frame->header.flags & FLAG_START_TASK,
           frame->header.transaction_id, frame->header.payload_len);
    print_payload(frame->payload, frame->header.payload_len);

    // Check control byte
    switch (frame->header.start_byte)
    {
    case 0x00: // Connection Close Frame
        printf("[Server] Client closed connection\n");
        return 2;
    case 0xAA: // Valid case
        break;
    default:
        printf("Invalid Start Byte\n");
        return -1; // Invalid start byte
    }

    // Call differenet message handler
    switch (frame->header.message_type)
    {
    case OPEN_TASK:
        printf("[Server] Handling OPEN_TASK message.\n");

        associated_transaction_id = msg_open_task(frame, server);

        return 0; // Send return frame back
    case CLOSE_TASK:
        break;
    case RETURN:
        msg_return(frame);
        break;
    case DATA_CHUNK:
        printf("[Server] Handling DATA_CHUNK message\n");
        associated_transaction_id = msg_data_chunk(frame);

        break;
    case ACK:
        break;
    case NACK:
        break;
    case HANDSHAKE:

        break;

    default:
        printf("Unknown message type: %02X\n", frame->header.message_type);
        return -2; // Unknown message type
    }

    return 0; // Success, no response needed
}