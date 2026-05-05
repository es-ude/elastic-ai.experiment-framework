#ifndef FRAME_H
#define FRAME_H

#include <stdint.h>

#define FRAME_OVERHEAD 5
#define CHECKSUM_SIZE 1

typedef struct
{
    uint8_t start_byte; // Always 0xAA
    uint8_t message_type;
    uint8_t flags;
    uint8_t msg_id;
    uint8_t payload_len;
} Frameheader;

typedef struct
{
    Frameheader header;
    uint8_t *payload;
} Frame;

typedef struct
{
    uint8_t socket;
    Frame frame;
} SendOrder;

#endif