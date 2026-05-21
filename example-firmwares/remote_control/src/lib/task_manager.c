#include "task_manager.h"
#include "frame_builder.h"
#include "sender.h"
#include "msg_types.h"
#include "embedded_functions.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FIXED_PAYLOAD_SIZE 2

// Task pool
static Task task_pool[MAX_TASKS] = {0}; // Support up to MAX_TASKS concurrent tasks
static uint8_t free_tasks = MAX_TASKS;

// Initialize the task management system
void init_tasks(void)
{
    for (int i = 0; i < MAX_TASKS; i++)
    {
        task_pool[i].id = i;
        task_pool[i].status = TASK_STATUS_IDLE;
        memset(task_pool[i].input_data, 0, TASK_BUFFER_LEN_BYTE);
        task_pool[i].input_data_len = 0;
        memset(task_pool[i].output_data, 0, TASK_BUFFER_LEN_BYTE);
        task_pool[i].output_data_len = 0;
        task_pool[i].fn_id = 0;
    }
}

// Enqueue a task to be processed by the tasks process.
void enqueue_task(RingBuffer *rb, Task *task)
{
    printf("[Task Manager] Enqueue task with values: \n task_id: %d, function_id: %d\n",
           task->id, task->fn_id);
    ringbuffer_push(rb, &task);
}

// Get one free task pointer. Does not reserve the Task already
Task *get_free_task()
{
    for (int i = 0; i < MAX_TASKS; i++)
    {
        if (task_pool[i].status == TASK_STATUS_IDLE)
        {
            return &task_pool[i];
        }
    }

    return NULL;
}

bool init_task(Task *self, Frame *frame)
{
    if (self->status != TASK_STATUS_IDLE)
    {
        return false; // Task already running
    }
    if (free_tasks == 0)
    {
        return false; // No free task slots available
    }

    free_tasks--;

    self->status = TASK_STATUS_PREPARING; // Mark as running
    self->fn_id = frame->payload[0];      // First Byte determines called function ID

    self->run = get_embedded_function(self->fn_id)->fnc_pointer;
    if (self->run == 0)
    {
        perror("No valid function id");
        return false;
    }

    printf("[Task] Task prepared with id %i and fn_id %i\n", self->id, self->fn_id);
    return true;
}

// @return @param bool if further Datachunks are expected
bool send_frame_to_task(RingBuffer *task_rb, Task *task, Frame *frame)
{
    memcpy(&task->input_data[task->input_data_len], frame->payload, frame->header.payload_len);

    task->input_data_len += frame->header.payload_len;

    if (task->run == NULL)
    {
        return false;
    }
    start_task(task_rb, task);
    return true;
}

// Frees the allocated Space for the Data of the Task and resets the values
bool finish_task(Task *self)
{
    self->status = TASK_STATUS_IDLE;
    self->fn_id = 0;

    self->input_data_len = 0;
    self->output_data_len = 0;

    self->run = NULL;
    free_tasks++;

    return true;
}

// Retrieve a pointer to a task by its ID. Returns NULL if the task ID is invalid or if the task is idle
Task *get_task_by_id(uint8_t task_id)
{
    if (task_id >= MAX_TASKS)
    {
        return NULL; // Invalid task ID or task is not running
    }
    return &task_pool[task_id];
}

// Starts a task by pushing it into the task queue
bool start_task(RingBuffer *rb, Task *task)
{
    task->status = TASK_STATUS_RUNNING;
    enqueue_task(rb, task); // Enqueue the task to be processed by the tasks thread
    printf("[Task] Started task with ID %i\n", task->id);
    return true;
}

void process_tasks(RingBuffer *task_rb, RingBuffer *outgoing_rb)
{
    Task *task;

    while (ringbuffer_pop(task_rb, &task))
    {
        if (task->run == NULL)
        {
            perror("Task was queued for execution without function pointer");
            return;
        }
        task->run(task);
        printf("[Task] Finished Task with id %i\n", task->id);
        fflush(stdout);
    }
}
