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
    if (task == NULL) {
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
    printf("[Server] Handle incoming data chunk\n");
    Task *task = get_task_by_id(frame->payload[0]); // Get the task ID from the first byte of the payload to identify which task this data chunk belongs to
    if (task == NULL)
    {
        printf("Invalid task ID in data chunk: %d\n", frame->payload[0]);
        return -1; // Invalid task ID
    }
    printf("[Server] Fetched Task with id %i\n", task->task_id);

    // Check if the DATA_CHUNK has an empty Data_payload (task_id and data_id are still there, so 2 means empty)
    // if yes, then that means the end of a DATA_CHUNK Stream and the intention of starting the Task
    if (frame->header.payload_len == 2)
    {
        task->stream_manager.incoming_connection.stream_status = STREAM_STATUS_CLOSED;
        int result = start_task(task); // Starts the task since it was the last Data_chunk
        return task->task_id;
    }

    // Append new data chunk to existing Data if it is not the last Data Chunk
    uint8_t *tmp = realloc(task->input_data, task->input_data_len + frame->header.payload_len - 1); // Resize the input data buffer to accommodate the new chunk

    if (tmp == NULL)
    {
        printf("Realloc failed");
        return -1;
    }
    task->input_data = tmp;

    // Copy the new chunk into the input data buffer
    uint8_t *buf = (uint8_t *)task->input_data;
    memcpy(
        &(buf[task->input_data_len]),
        &frame->payload[2],
        frame->header.payload_len - 1);

    task->input_data_len += frame->header.payload_len - 1; // Update the input data length
    return task->task_id;
}

/*
 * Handles the frame interpreation.
 * @return Return code:
 *          0: no frame should be sent back
 *          1: send the "response" frame
 *          2: Connection Close Frame
 *          -1: error code
 */
int handle_incoming_frame(Frame *frame, Server server, Frame *response)
{
    int task_id;

    printf("\n[Server] Received frame \n Control Byte: %02X, Type: %02X, Flags: %02X, Msg ID: %02X, "
           "Payload Len: %d\n\n",
           frame->header.start_byte, frame->header.message_type, frame->header.flags,
           frame->header.msg_id, frame->header.payload_len);
    print_payload(frame->payload, frame->header.payload_len);

    if (frame->header.start_byte == 0x0)
    {
        printf("[Server] Client closed connection\n");
        return 2;
    } // Connection Close Frame

    if (frame->header.start_byte != 0xAA)
    {
        printf("Invalid Start Byte\n");
        return -1; // Invalid start byte
    }

    switch (frame->header.message_type)
    { // Start different tasks based on message type
    case OPEN_TASK:
        printf("[Server] Handling OPEN_TASK message.\n");

        task_id = msg_open_task(frame, server);

        // Create the frame for immediate return
        frame_builder_return(response, 0x00, (task_id >= 0) ? 0x00 : 0x01, task_id,
                             frame->header.msg_id); // Return success or failure code along with the
                                                    // task ID and caller message ID for tracking

        return 1; // Send return frame back
    case CLOSE_TASK:
        break;
    case RETURN:
        msg_return(frame);
        break;
    case DATA_CHUNK:
        printf("[Server] Handling DATA_CHUNK message\n");
        task_id = msg_data_chunk(frame);

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