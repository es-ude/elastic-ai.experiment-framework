#include "frame_builder.h"
#include "msg_types.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/**
 *  Builds a RETURN frame with specified parameters
 *
 */
int frame_builder_return(Frame *frame, uint8_t flags, uint8_t return_code, uint8_t transaction_id)
{
    frame->header.start_byte = 0xAA;
    frame->header.message_type = RETURN; // Use RETURN message type to send back the task ID
    frame->header.flags = flags;
    frame->header.payload_len = 3;
    frame->header.transaction_id = transaction_id;

    // Set payload (see draft_protocol.md)
    frame->payload[0] = return_code;
    return 0;
}

int frame_builder_data_chunk(Frame *frame, uint8_t flags, uint8_t *data, uint8_t data_len,
                             uint8_t transaction_id, uint8_t starting_data_id, uint64_t max_chunk_size)
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
    frame->header.message_type = DATA_CHUNK;
    frame->header.flags = flags;
    frame->header.payload_len = data_len;
    frame->header.transaction_id = transaction_id;

    // Only set payload when true
    if (data_len > 0)
    {
        memcpy(frame->payload, data, data_len);
    }

    return amount_chunks;
}

int frame_builder_open_task(Frame *frame, uint8_t transaction_id, uint8_t flags, uint8_t function_id)
{
    frame->header.start_byte = 0xAA;
    frame->header.message_type = OPEN_TASK;
    frame->header.flags = flags;
    frame->header.payload_len = 1;
    frame->header.transaction_id = transaction_id;

    // Set payload (see draft_protocol.md)
    frame->payload[0] = function_id;
    return 0;
}
