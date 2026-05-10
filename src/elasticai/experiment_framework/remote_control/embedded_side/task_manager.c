#include "task_manager.h"
#include "connection_manager.h"
#include "frame_builder.h"
#include "sender.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

ThreadSafeQueue *task_pointer_queue = NULL;

// Task pool
Task tasks[MAX_TASKS];           // Support up to MAX_TASKS concurrent tasks
bool free_task_slots[MAX_TASKS]; // contains free task indices
int free_tasks;

// Initialize the task management system by marking all task slots as free.
void init_tasks()
{
    for (int i = 0; i < MAX_TASKS; i++)
    {
        tasks[i].task_id = i;
        tasks[i].init = init;
        tasks[i].finish = finish;
        tasks[i].status = TASK_STATUS_IDLE; // Mark all tasks as idle

        free_task_slots[i] = true; // Mark all task slots as free
    }

    free_tasks = MAX_TASKS; // All tasks are initially free

    task_pointer_queue = queue_create(QUEUE_TASK_LEN, sizeof(Task *));
}

// Enqueue a task to be processed by the tasks thread. This function is thread-safe and can be
// called from any thread to queue a new task for execution.
void enqueue_task(Task *task)
{
    printf("[Task Manager] Enqueue task with values: \n task_id: %d, function_id: %d, stream_outgoing: %d, "
           "stream_incoming: %d\n",
           task->task_id, task->function_id, task->stream_manager.outgoing_connection.connection_fd,
           task->stream_manager.incoming_connection.connection_fd);
    queue_push(task_pointer_queue, &task);
}

// Dequeue a task to be processed by the tasks thread. This function will block if the queue is
// empty until a new task is enqueued.
Task *dequeue_task()
{
    Task *task;
    queue_pop(task_pointer_queue, &task);
    return task;
}

// Get one free task. Does not reserve the Task already
Task *get_free_task()
{
    for (int i = 0; i < MAX_TASKS; i++)
    {
        if (free_task_slots[i])
        {
            printf("[Task] Got Task with ID %i", i);
            return &tasks[i];
        }
    }

    return NULL;
}

bool init(Task *self, Frame *frame, uint8_t incoming_fd, uint8_t outgoing_fd)
{
    if (free_tasks == 0)
    {
        return false; // No free task slots available
    }
    if (self->status != TASK_STATUS_IDLE)
    {
        return false; // Task already running
    }

    free_task_slots[self->task_id] = false; // Set Task as occupied
    free_tasks--;

    self->status = TASK_STATUS_PREPARING;  // Mark as running
    self->function_id = frame->payload[0]; // First Byte determines called function ID

    self->input_data_len = frame->header.payload_len - 1; // Length of the input data
    self->input_data = malloc(self->input_data_len);

    StreamManager stream_manager = {.incoming_connection = {.stream_status = STREAM_STATUS_OPEN,
                                                            .connection_fd = incoming_fd,
                                                            .bytes_transferred = 0},
                                    .outgoing_connection = {.stream_status = STREAM_STATUS_OPEN,
                                                            .connection_fd = outgoing_fd,
                                                            .bytes_transferred = 0}};

    self->stream_manager = stream_manager; // Associate the task with the provided stream
                                           // manager for handling its data streams

    self->run = get_embedded_function_pointer(self->function_id);

    printf("[Task] Task prepared with id %i and fnc_id %i\n", self->task_id, self->function_id);
}

// Frees the allocated Space for the Data of the Task and resets the values
bool finish(Task *self)
{
    self->status = TASK_STATUS_IDLE;
    self->function_id = 0;

    free(self->input_data);
    self->input_data = NULL;
    self->input_data_len = 0;

    free(self->output_data);
    self->output_data = NULL;
    self->output_data_len = 0;

    self->run = NULL;
    free_task_slots[self->task_id] = true;
    free_tasks++;

    return true;
}

// Retrieve a pointer to a task by its ID. Returns NULL if the task ID is invalid or if the task is idle
Task *get_task_by_id(uint8_t task_id)
{
    if (task_id >= MAX_TASKS || tasks[task_id].status == TASK_STATUS_IDLE)
    {
        return NULL; // Invalid task ID or task is not running
    }
    return &tasks[task_id];
}

// Starts a task by pushing it into the task queue
int start_task(Task *task)
{
    task->status = TASK_STATUS_RUNNING;
    enqueue_task(task); // Enqueue the task to be processed by the tasks thread
    printf("[Task] Started task with ID %i\n", task->task_id);
    return 0;
}

// Runs Tasks that were added to to task queue. Sends Reply messages if necessary
void *tasks_thread(void *arg)
{
    Frame response_frame;
    Task *task;

    init_tasks(); // Initialize the task management system

    while (1)
    {
        task = dequeue_task(); // Wait for a task to be enqueued by the server thread when a
                               // new OPEN_TASK message is received
        printf("[Task] Processing task with ID: %d\n", task->task_id);

        ReturnValue result = task->run(task->input_data); // Execute the function associated with the task using its input data

        task->output_data = result.raw_data; // Store the result in the task's output data field
        task->output_data_len = result.raw_data_len;

        int msg_type = result.return_msg_id;
        switch (msg_type)
        {
        case RETURN:
            frame_builder_return(&response_frame, 0x00, 0x00, task->task_id,
                                 task->task_id);
        case DATA_CHUNK:
            frame_builder_data_chunk(&response_frame, 0x00, task->output_data, task->output_data_len, task->task_id, 0, 1024);
            queue_push(outgoing_queue,
                       &(SendOrder){.fd = task->stream_manager.outgoing_connection.connection_fd,
                                    .frame = response_frame}); // send Data first
            frame_builder_return(&response_frame, 0x00, 0x00, task->task_id,
                                 task->task_id); // send a return as last step
        }

        queue_push(outgoing_queue,
                   &(SendOrder){.fd = task->stream_manager.outgoing_connection.connection_fd,
                                .frame = response_frame});
    }
    return NULL;
}