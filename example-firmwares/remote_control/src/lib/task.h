#pragma once

#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>

#include "frame.h"
#include "ringbuffer.h"

typedef struct Task Task;
typedef struct TaskServices TaskServices;

#define TASK_BUFFER_LEN_BYTE 1024
#define MAX_TASKS 32

typedef enum
{
    TASK_STATUS_IDLE,
    TASK_STATUS_PREPARING,
    TASK_STATUS_SETUP,
    TASK_STATUS_RUNNING,
    TASK_STATUS_FINISHING

} TaskStatus;

struct TaskServices
{
    RingBuffer *outgoing_rb;
    uint8_t task_id;

    uint8_t (*send_return)(TaskServices *task_s, uint8_t flags, uint32_t return_code, bool add_checksum);
    uint8_t (*send_data)(TaskServices *task_s, uint8_t flags, uint8_t *data, uint32_t data_len, bool add_checksum);
};

typedef struct
{
    TaskServices task_services;

    uint16_t step_index;

    /* --- function execution --- */
    uint8_t input_data[TASK_BUFFER_LEN_BYTE];
    uint32_t input_data_len;
    uint8_t output_data[TASK_BUFFER_LEN_BYTE];
    uint32_t output_data_len;

} TaskContext;

typedef void (*Func)(TaskContext *task_context);

typedef struct
{
    Func setup;
    Func handle;
    Func tear_down;
} TaskDefinition;

struct Task
{
    uint8_t id;

    TaskStatus status;

    TaskContext ctx;

    uint8_t task_definition_id;
    TaskDefinition *funcs;
};
