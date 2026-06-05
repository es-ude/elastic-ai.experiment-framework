#include "task_definitions.h"
#include "msg_types.h"
#include "frame_builder.h"

#include <stdio.h>
#include <string.h>

void default_setup(TaskContext *task_context)
{
}

void default_teardown(TaskContext *task_context)
{
}

void send_mirror_reply(TaskContext *task_context)
{
    memcpy(task_context->output_data, task_context->input_data, task_context->input_data_len);
    task_context->output_data_len = task_context->input_data_len;

    task_context->task_services.send_data(&task_context->task_services, 0, task_context->output_data, task_context->output_data_len);
    task_context->task_services.send_return(&task_context->task_services, 0, 0);
}

void func1(TaskContext *task_context)
{
    char *msg = "func1 called";
}

void request_ack_from_pc(TaskContext *task_context)
{
    char *msg = "test data";

    task_context->task_services.send_data(&task_context->task_services, FLAG_NEED_ACK, (uint8_t *)msg, strlen(msg));
}

void fast_setup_ack_from_pc(TaskContext *task_context)
{
    request_ack_from_pc(task_context);
}

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id

static TaskDefinition task_definition_table[] = {
    {.setup = default_setup,
     .tear_down = default_teardown,
     .handle = send_mirror_reply},
    {.setup = default_setup,
     .tear_down = default_teardown,
     .handle = func1},
    {.setup = default_setup,
     .handle = request_ack_from_pc,
     .tear_down = default_teardown}};

static UserTasks user_task_defintions = {.task_definitions = task_definition_table,
                                         .size = sizeof(task_definition_table)};

TaskDefinition *get_task_definition(uint32_t task_definition_id)
{
    if (user_task_defintions.size == 0)
    {
        return NULL;
    }

    if (task_definition_id < 0 || task_definition_id >= user_task_defintions.size / sizeof(TaskDefinition))
    {
        return NULL;
    }
    return &user_task_defintions.task_definitions[task_definition_id];
}
