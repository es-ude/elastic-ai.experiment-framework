#include "frame_builder.h"
#include "msg_types.h"
#include "log.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

uint8_t crc8(const uint8_t *data, size_t length)
{
    uint8_t crc = 0x00;

    for (size_t i = 0; i < length; i++)
    {
        crc ^= data[i];

        for (uint8_t bit = 0; bit < 8; bit++)
        {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;
            else
                crc <<= 1;
        }
    }

    return crc;
}

int add_checksum(Frame *frame)
{
    if (frame->header.payload_len + 1 > MAX_PAYLOAD)
    {
        LOG("Frame too big for adding checksum!");
        return -1;
    }
    uint8_t checksum = crc8((uint8_t *)frame, FRAME_OVERHEAD + frame->header.payload_len);
    frame->payload[frame->header.payload_len] = checksum;
}

int frame_builder_return(Frame *frame, uint8_t flags, uint8_t return_code, uint8_t transaction_id, bool checksum_needed)
{

    *frame = (Frame){
        .header = {
            .start_byte = 0xAA,
            .message_type = RETURN,
            .flags = flags,
            .transaction_id = transaction_id,
            .payload_len = 1},
        .payload[0] = return_code};

    if (checksum_needed)
    {
        add_checksum(frame);
    }
    return 0;
}

int frame_builder_data_chunk(Frame *frame, uint8_t flags, uint8_t *data, uint16_t data_len,
                             uint8_t transaction_id, uint8_t starting_data_id, uint64_t max_chunk_size, bool checksum_needed)
{

    if (frame == NULL)
    {
        LOG("frame_builder_data_chunk: frame is NULL\n");
        return -1;
    }

    if (data_len > 0 && data == NULL)
    {
        LOG("frame_builder_data_chunk: data is NULL but data_len > 0\n");
        return -1;
    }

    // Split the data into chunks if it exceeds the maximum chunk size
    if (max_chunk_size != 0 && data_len > max_chunk_size) // if chunk size 0 assume we dont want chunking
    {
        // Handle chunking logic here (not implemented in this example)
        LOG("Data length exceeds maximum chunk size. Chunking not implemented yet.\n");
        return -1;
    }
    int amount_chunks = 1; // Fixed for now

    size_t payload_capacity = sizeof(frame->payload);

    if (data_len > payload_capacity)
    {
        LOG("frame_builder_data_chunk: data_len (%u) exceeds payload capacity (%zu)\n",
            data_len, payload_capacity);
        return -1;
    }

    *frame = (Frame){
        .header = {
            .start_byte = 0xAA,
            .message_type = DATA_CHUNK,
            .flags = flags,
            .payload_len = data_len,
            .transaction_id = transaction_id}};

    // Only set payload when true
    if (data_len > 0)
    {
        memcpy(frame->payload, data, data_len);
    }

    if (checksum_needed)
    {
        add_checksum(frame);
    }

    LOG("[Frame Builder] built datachunk frame\n");
    return amount_chunks;
}

int frame_builder_nack(Frame *frame, uint8_t transaction_id, uint8_t data_id, uint8_t nack_code)
{
    *frame = (Frame){
        .header = {
            .start_byte = 0xAA,
            .message_type = NACK,
            .flags = 0,
            .msg_id = data_id,
            .payload_len = 1,
            .transaction_id = transaction_id},
        .payload[0] = nack_code};

    return 0;
}

int frame_builder_ack(Frame *frame, uint8_t transaction_id, uint8_t data_id)
{
    *frame = (Frame){
        .header = {
            .start_byte = 0xAA,
            .message_type = ACK,
            .flags = 0,
            .msg_id = data_id,
            .payload_len = 0,
            .transaction_id = transaction_id}};

    return 0;
}

int frame_builder_open_task(Frame *frame, uint8_t transaction_id, uint8_t flags, uint8_t function_id, bool checksum_needed)
{
    *frame = (Frame){
        .header = {
            .start_byte = 0xAA,
            .message_type = OPEN_TASK,
            .flags = flags,
            .payload_len = 1,
            .transaction_id = transaction_id},
        .payload[0] = function_id};

    if (checksum_needed)
    {
        add_checksum(frame);
    }

    return 0;
}
