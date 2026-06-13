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

int frame_builder_data_chunk(Frame *frame, uint8_t flags, uint8_t *data, uint16_t data_len,
                             uint8_t transaction_id, uint8_t starting_data_id, uint64_t max_chunk_size)
{

    if (frame == NULL)
    {
        printf("frame_builder_data_chunk: frame is NULL\n");
        fflush(stdout);
        return -1;
    }

    if (data_len > 0 && data == NULL)
    {
        printf("frame_builder_data_chunk: data is NULL but data_len > 0\n");
        fflush(stdout);
        return -1;
    }

    // Split the data into chunks if it exceeds the maximum chunk size
    if (max_chunk_size != 0 && data_len > max_chunk_size) // if chunk size 0 assume we dont want chunking
    {
        // Handle chunking logic here (not implemented in this example)
        printf("Data length exceeds maximum chunk size. Chunking not implemented yet.\n");
        fflush(stdout);
        return -1;
    }
    int amount_chunks = 1; // Fixed for now

    size_t payload_capacity = sizeof(frame->payload);

    if (data_len > payload_capacity)
    {
        printf("frame_builder_data_chunk: data_len (%u) exceeds payload capacity (%zu)\n",
               data_len, payload_capacity);
        fflush(stdout);
        return -1;
    }

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

    printf("[Frame Builder] built datachunk frame\n");
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
