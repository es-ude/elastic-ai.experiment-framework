#include "task_manager.h"
#include "frame_builder.h"
#include "sender.h"
#include "msg_types.h"
#include "task_definitions.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FIXED_PAYLOAD_SIZE 2

// Initialize the task management system
void init_task_manager(RingBuffer *outgoing_rb, TaskManager *task_manager, TaskContext ctx)
{
    *task_manager = (TaskManager){
        .task_pool = {0},
        .free_tasks = MAX_TASKS,
        .ctx = ctx};

    for (int i = 0; i < MAX_TASKS; i++)
    {

        Task *task = &task_manager->task_pool[i];
        task->id = i;
        task->status = TASK_STATUS_IDLE;
        memset(task->input_data, 0, TASK_BUFFER_LEN_BYTE);
        task->input_data_len = 0;
        memset(task->output_data, 0, TASK_BUFFER_LEN_BYTE);
        task->output_data_len = 0;
        task->task_definition_id = 0;
        task->ctx = &task_manager->ctx;
    }
}

// Enqueue a task to be processed by the tasks process.
void enqueue_task(RingBuffer *rb, Task *task)
{
    printf("[Task Manager] Enqueue task with values: \n task_id: %d, function_id: %d\n",
           task->id, task->task_definition_id);
    ringbuffer_push(rb, &task);
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

bool init_task(Task *self, Frame *frame, TaskManager *task_manager)
{
    if (self->status != TASK_STATUS_IDLE)
    {
        return false; // Task already running
    }
    if (task_manager->free_tasks == 0)
    {
        return false; // No free task slots available
    }

    task_manager->free_tasks--;

    self->status = TASK_STATUS_PREPARING;         // Mark as running
    self->task_definition_id = frame->payload[0]; // First Byte determines called function ID

    self->funcs = get_task_definition(self->task_definition_id);
    if (self->funcs == NULL)
    {
        perror("No valid function id");
        return false;
    }

    if (self->funcs->setup == NULL)
    {
        return true;
    }
    self->funcs->setup(self);

    return true;
}

// @return @param bool if further Datachunks are expected
bool send_frame_to_task(RingBuffer *task_rb, Task *task, Frame *frame)
{
    memcpy(&task->input_data[task->input_data_len], frame->payload, frame->header.payload_len);

    task->input_data_len += frame->header.payload_len;

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
        task->funcs->tear_down(task);
    }

    task->status = TASK_STATUS_IDLE;
    task->task_definition_id = 0;

    task->input_data_len = 0;
    task->output_data_len = 0;

    task->funcs = NULL;
    task_manager->free_tasks++;

    printf("[Task] Finished Task with id %i\n", task->id);
    fflush(stdout);

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
    printf("[Task] Started task with ID %i\n", task->id);
    return true;
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
        task->funcs->handle(task);
    }
}
