#pragma once

#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>

#include "frame.h"
#include "transport.h"
#include "ringbuffer.h"

typedef struct Task Task;

#define TASK_BUFFER_LEN_BYTE 1024

typedef enum
{
    TASK_STATUS_IDLE = 0,
    TASK_STATUS_PREPARING = 1,
    TASK_STATUS_RUNNING = 2

} TaskStatus;

struct Task
{
    uint8_t id;
    uint16_t step_index;
    TaskStatus status;

    /* --- function execution --- */
    uint8_t input_data[TASK_BUFFER_LEN_BYTE];
    uint32_t input_data_len;
    uint8_t output_data[TASK_BUFFER_LEN_BYTE];
    uint32_t output_data_len;

    RingBuffer *outgoing_rb; // for sending data back to client
    uint8_t fn_id;
    void (*run)(Task *task);
};
