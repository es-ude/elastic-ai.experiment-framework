#ifndef FRAME_H
#define FRAME_H

#include <stdint.h>

#define FRAME_OVERHEAD 7
#define CHECKSUM_SIZE 1
#define MAX_PAYLOAD 256

// Flags. |= to set, & to check
#define FLAG_NEED_ACK (1 << 0)
#define FLAG_HAS_CRC (1 << 1)

typedef struct __attribute__((packed))
{
    uint8_t start_byte; // Always 0xAA
    uint8_t message_type;
    uint8_t flags;
    uint8_t transaction_id;
    uint8_t msg_id;
    uint16_t payload_len;
} Frameheader;

typedef struct
{
    Frameheader header;
    uint8_t payload[MAX_PAYLOAD];
} Frame;

#endif