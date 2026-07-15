#include "task_definition_host.h"
#include <string.h>
#include <stdbool.h>
#include <stdio.h>

#include "log.h"

void send_mirror_reply(TaskContext *task_context)
{
    LOG("send_mirror_reply called\n");
    memcpy(task_context->output_data, task_context->input_data, task_context->input_data_len);
    task_context->output_data_len = task_context->input_data_len;

    LOG("Output data len: %d\n", task_context->output_data_len);
    LOG("Preparing response frame with payload\n");

    task_context->task_services.send_data(&task_context->task_services, 0, task_context->output_data, task_context->output_data_len, false);

    LOG("task 1 %p", (void *)task_context);
    LOG("Preparing response frame with payload onto ringbuffer %p\n", (void *)task_context->task_services.outgoing_rb);

    LOG("Prepared return frame\n");

    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void func1(TaskContext *task_context)
{
    LOG("Function 1 executed\n");
    char *msg = "func1 called";
}

void request_ack_from_pc(TaskContext *task_context)
{
    char *msg = "test data";

    task_context->task_services.send_data(&task_context->task_services, FLAG_NEED_ACK, (uint8_t *)msg, strlen(msg), false);
}

void default_setup(TaskContext *task_context)
{
    LOG("Task %i was setup\n", task_context->task_services.task_id);
}

void fast_setup_ack_from_pc(TaskContext *task_context)
{
    request_ack_from_pc(task_context);
}

void default_teardown(TaskContext *task_context)
{
    LOG("Task %i was torn down\n", task_context->task_services.task_id);
}