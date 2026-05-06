#include "frame_builder.h"
#include "enums.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/**
 *  Builds a RETURN frame with specified parameters
 *
 */
int frame_builder_return(Frame *frame, uint8_t flags, uint8_t return_code, uint8_t task_id,
                         uint8_t caller_msg_id)
{
    frame->header.start_byte = 0xAA;
    frame->header.message_type = RETURN; // Use RETURN message type to send back the task ID
    frame->header.flags = flags;
    frame->header.payload_len = 3;

    // Set payload (see draft_protocol.md)
    frame->payload = malloc(frame->header.payload_len);
    frame->payload[0] = return_code;
    frame->payload[1] = task_id;
    frame->payload[2] = caller_msg_id;
    return 0;
}

int frame_builder_data_chunk(Frame *frame, uint8_t flags, uint8_t *data, uint8_t data_len,
                             uint8_t task_id, uint8_t starting_data_id, uint64_t max_chunk_size)
{
    // Split the data into chunks if it exceeds the maximum chunk size
    if (data_len > max_chunk_size)
    {
        // Handle chunking logic here (not implemented in this example)
        printf("Data length exceeds maximum chunk size. Chunking not implemented yet.\n");
        return -1;
    }
    int amount_chunks = 1; // Fixed for now

    // Assume only one chunk for now
    frame->header.start_byte = 0xAA;
    frame->header.message_type = DATA_CHUNK; // Use DATA_CHUNK message type to send back the function result
    frame->header.flags = flags;
    frame->header.payload_len = 2 + data_len;

    // Only set payload when true
    if (data_len > 0)
    {
        // Set payload (see draft_protocol.md)
        frame->payload = malloc(frame->header.payload_len);
        frame->payload[0] = task_id;
        frame->payload[1] = starting_data_id;       // running index of data chunk
        memcpy(&frame->payload[2], data, data_len); // Copy the function result data into the payload
    }

    return amount_chunks;
}

int frame_builder_open_task(Frame *frame, uint8_t flags, uint8_t function_id)
{
    frame->header.start_byte = 0xAA;
    frame->header.message_type = OPEN_TASK;
    frame->header.flags = flags;
    frame->header.payload_len = 1;

    // Set payload (see draft_protocol.md)
    frame->payload = malloc(frame->header.payload_len);
    frame->payload[0] = function_id;
    return 0;
}