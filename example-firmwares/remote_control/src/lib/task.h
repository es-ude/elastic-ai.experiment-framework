#pragma once

#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>

#include "frame.h"
#include "ringbuffer.h"

typedef struct Task Task;

#define TASK_BUFFER_LEN_BYTE 1024

typedef enum
{
    TASK_STATUS_IDLE,
    TASK_STATUS_PREPARING,
    TASK_STATUS_SETUP,
    TASK_STATUS_RUNNING,
    TASK_STATUS_FINISHING

} TaskStatus;

typedef struct
{
    RingBuffer *outgoing_rb; // for sending data back to client
} TaskContext;

typedef void (*Func)(Task *task);

typedef struct
{
    Func setup;
    Func handle;
    Func tear_down;
} TaskDefinition;

struct Task
{
    TaskContext *ctx;

    uint8_t id;
    uint16_t step_index;
    TaskStatus status;

    /* --- function execution --- */
    uint8_t input_data[TASK_BUFFER_LEN_BYTE];
    uint32_t input_data_len;
    uint8_t output_data[TASK_BUFFER_LEN_BYTE];
    uint32_t output_data_len;

    uint8_t task_definition_id;
    TaskDefinition *funcs;
};
