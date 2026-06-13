#include "task_definitions.h"
#include "msg_types.h"
#include "frame_builder.h"

#include <stdio.h>
#include <string.h>

void default_setup(Task *task)
{
    printf("Task %i was setup with definition %i\n", task->id, task->task_definition_id);
    fflush(stdout);
}

void default_teardown(Task *task)
{
    printf("Task %i was finished with definition %i\n", task->id, task->task_definition_id);
    fflush(stdout);
}

void send_mirror_reply(Task *task)
{
    printf("send_mirror_reply called\n");
    memcpy(task->output_data, task->input_data, task->input_data_len);
    task->output_data_len = task->input_data_len;

    Frame frame = {0};
    printf("Output data len: %d\n", task->output_data_len);
    printf("Preparing response frame with payload\n");

    frame_builder_data_chunk(&frame, 0, task->output_data, task->output_data_len, task->id, 0, 0);
    printf("task 1 %p", (void *)task);
    fflush(stdout);
    printf("task 2 %p", (void *)task->ctx);
    fflush(stdout);
    printf("Preparing response frame with payload onto ringbuffer %p\n", (void *)task->ctx->outgoing_rb);
    fflush(stdout);
    ringbuffer_push(task->ctx->outgoing_rb, &frame);

    printf("Prepared return frame\n");
    fflush(stdout);
    frame = (Frame){0};
    frame_builder_return(&frame, 0, 0, task->id);
    ringbuffer_push(task->ctx->outgoing_rb, &frame);
}

void func1(Task *task)
{
    printf("Function 1 executed\n");
    char *msg = "func1 called";
}

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id
static TaskDefinition function_table[] = {
    {.setup = default_setup,
     .tear_down = default_teardown,
     .handle = send_mirror_reply},
    {.setup = default_setup,
     .tear_down = default_teardown,
     .handle = func1}};

TaskDefinition *get_task_definition(int function_id)
{
    if (function_id < 0 || function_id >= sizeof(function_table) / sizeof(TaskDefinition))
    {
        printf("Invalid function ID: %d\n", function_id);
        fflush(stdout);
        return NULL;
    }
    return &function_table[function_id];
}