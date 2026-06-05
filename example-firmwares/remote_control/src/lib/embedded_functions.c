#include "embedded_functions.h"
#include "msg_types.h"
#include "frame_builder.h"

#include <stdio.h>
#include <string.h>

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id
static FuncMetadata function_table[] = {
    {.fnc_pointer = send_mirror_reply},
    {.fnc_pointer = func1}};

FuncMetadata *get_embedded_function(int function_id)
{
    if (function_id < 0 || function_id >= sizeof(function_table) / sizeof(FuncMetadata))
    {
        printf("Invalid function ID: %d\n", function_id);
        fflush(stdout);
        return NULL;
    }
    return &function_table[function_id];
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
    ringbuffer_push(task->outgoing_rb, &frame);

    printf("Prepared return frame\n");
    fflush(stdout);
    frame = (Frame){0};
    frame_builder_return(&frame, 0, 0, task->id);
    ringbuffer_push(task->outgoing_rb, &frame);
}

void func1(Task *task)
{
    printf("Function 1 executed\n");
    char *msg = "func1 called";
}