#include "task_manager.h"
#include "frame_builder.h"
#include "sender.h"
#include "msg_types.h"
#include "log.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FIXED_PAYLOAD_SIZE 2

static UserTasks user_task_defintions;

// Initialize the task management system
void init_task_manager(RingBuffer *outgoing_rb, TaskManager *task_manager, TaskDefinition *task_definition_table, uint32_t task_definition_table_size)
{

    *task_manager = (TaskManager){
        .task_pool = {0},
        .free_tasks = MAX_TASKS};

    for (int i = 0; i < MAX_TASKS; i++)
    {
        Task *task = &task_manager->task_pool[i];
        task->id = i;
        task->status = TASK_STATUS_IDLE;
        task->ctx.task_services.task_id = i;
        task->ctx.task_services.send_data = send_data;
        task->ctx.task_services.send_return = send_return;
        task->ctx.task_services.outgoing_rb = outgoing_rb;
    }

    user_task_defintions = (UserTasks){.task_definitions = task_definition_table,
                                       .size = task_definition_table_size};
}

// Enqueue a task to be processed by the tasks process.
void enqueue_task(RingBuffer *rb, Task *task)
{
    LOG("[Task Manager] Enqueue task with values: \n task_id: %d, function_id: %d\n",
        task->id, task->task_definition_id);
    if (!ringbuffer_push(rb, &task))
    {
        LOG("[Task Manager] Failed to enqueue task with id %d\n", task->id);
    };
}

// Get one free task pointer. Does not reserve the Task already
Task *get_free_task(TaskManager *task_manager)
{
    for (int i = 0; i < MAX_TASKS; i++)
    {
        if (task_manager->task_pool[i].status == TASK_STATUS_IDLE)
        {
            return &task_manager->task_pool[i];
        }
    }

    return NULL;
}

bool init_task(Task *task, Frame *frame, TaskManager *task_manager)
{
    if (task->status != TASK_STATUS_IDLE)
    {
        return false; // Task already running
    }
    if (task_manager->free_tasks == 0)
    {
        return false; // No free task slots available
    }

    task_manager->free_tasks--;

    task->status = TASK_STATUS_PREPARING;         // Mark as running
    task->task_definition_id = frame->payload[0]; // First Byte determines called function ID

    task->funcs = get_task_definition(task->task_definition_id);
    if (task->funcs == NULL)
    {
        perror("No valid function id");
        return false;
    }

    if (task->funcs->setup == NULL)
    {
        return true;
    }
    task->funcs->setup(&task->ctx);

    return true;
}

// @return @param bool if further Datachunks are expected
bool send_frame_to_task(RingBuffer *task_rb, Task *task, Frame *frame)
{
    memcpy(&task->ctx.input_data[task->ctx.input_data_len], frame->payload, frame->header.payload_len);

    task->ctx.input_data_len += frame->header.payload_len;

    if (task->funcs == NULL || task->funcs->handle == NULL)
    {
        return false;
    }
    start_task(task_rb, task);
    return true;
}

bool finish_task(Task *task, TaskManager *task_manager)
{
    if (task->funcs != NULL && task->funcs->tear_down != NULL)
    {
        task->funcs->tear_down(&task->ctx);
    }

    task->status = TASK_STATUS_IDLE;
    task->task_definition_id = 0;

    task->ctx.input_data_len = 0;
    task->ctx.output_data_len = 0;

    task->ctx.step_counter = 0;

    task->funcs = NULL;
    task_manager->free_tasks++;
    free(task->ctx.user_data);
    task->ctx.user_data = NULL;

    LOG("[Task] Finished Task with id %i\n", task->id);

    return true;
}

// Retrieve a pointer to a task by its ID. Returns NULL if the task ID is invalid
Task *get_task_by_id(uint8_t task_id, TaskManager *task_manager)
{
    if (task_id >= MAX_TASKS || task_id < 0)
    {
        return NULL;
    }
    return &task_manager->task_pool[task_id];
}

// Starts a task by pushing it into the task queue
bool start_task(RingBuffer *rb, Task *task)
{
    task->status = TASK_STATUS_RUNNING;
    enqueue_task(rb, task); // Enqueue the task to be processed by the tasks thread
    LOG("[Task] Started task with ID %i\n", task->id);
    return true;
}

TaskDefinition *get_task_definition(uint32_t task_definition_id)
{
    if (user_task_defintions.size == 0)
    {
        LOG("no task definitions are set");
        return NULL;
    }

    if (task_definition_id >= user_task_defintions.size)
    {
        LOG("Invalid function ID: %d\n", task_definition_id);
        return NULL;
    }
    return &user_task_defintions.task_definitions[task_definition_id];
}

void process_tasks(RingBuffer *task_rb, RingBuffer *outgoing_rb, TaskManager *task_manager)
{
    Task *task;

    while (ringbuffer_pop(task_rb, &task))
    {
        if (task->funcs == NULL || task->funcs->handle == NULL)
        {
            perror("Task was queued for execution without function pointer");
            return;
        }
        task->funcs->handle(&task->ctx);
    }
}
