#ifndef FRAME_H
#define FRAME_H

#include <stdint.h>

#define FRAME_OVERHEAD 6
#define CHECKSUM_SIZE 1

#define DATACHUNK_PAYLOAD_STATIC_SIZE 1
#define RETURN_PAYLOAD_STATIC_SIZE 1
#define OPEN_TASK_STATIC_SIZE 1

// Flags. |= to set, & to check
#define FLAG_NEED_ACK (1 << 0)
#define FLAG_HAS_CRC (1 << 1)
#define FLAG_START_TASK (1 << 2)

typedef struct
{
    uint8_t start_byte; // Always 0xAA
    uint8_t message_type;
    uint8_t flags;
    uint8_t transaction_id;
    uint16_t payload_len;
} Frameheader;

typedef struct
{
    Frameheader header;
    uint8_t *payload;
} Frame;

typedef struct
{
    uint8_t fnc_id;
    uint8_t payload[];
} OpenTaskPayload; // WIP

typedef struct
{
    uint8_t data_id;
    uint8_t payload[];
} DataChunkPayload;

typedef struct
{
    uint8_t return_code;
    uint8_t payload[];
} ReturnPayload;

typedef struct
{
    uint8_t data_id;
    uint8_t payload[];
} AckPayload;

typedef struct
{
    uint8_t data_id;
    uint8_t payload[];
} NackPayload;

#endif