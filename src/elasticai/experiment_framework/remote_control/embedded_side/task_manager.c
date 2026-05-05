#include "task_manager.h"
#include "enums.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

// Task pool
Task tasks[MAX_TASKS];          // Support up to MAX_TASKS concurrent tasks
int free_task_slots[MAX_TASKS]; // contains free task indices
int free_tasks;

// Queued Tasks
Task task_queue[MAX_TASKS]; // Support up to MAX_TASKS concurrent tasks
int task_queue_head = 0, task_queue_tail = 0;

pthread_mutex_t task_queue_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t task_queue_cond = PTHREAD_COND_INITIALIZER;

// Initialize the task management system by marking all task slots as free.
void init_tasks()
{
    for (int i = 0; i < MAX_TASKS; i++)
    {
        tasks[i].task_id = i;
        tasks[i].status = TASK_STATUS_IDLE; // Mark all tasks as idle
    }

    for (int i = 0; i < MAX_TASKS; i++)
    {
        free_task_slots[i] = i; // Mark all task slots as free
    }
    free_tasks = MAX_TASKS; // All tasks are initially free
}

// Enqueue a task to be processed by the tasks thread. This function is thread-safe and can be
// called from any thread to queue a new task for execution.
void enqueue_task(Task *task)
{
    printf("[Task Manager] Enqueue task with values: \n task_id: %d, function_id: %d, stream_outgoing: %d, "
           "stream_incoming: %d\n",
           task->task_id, task->function_id, task->stream_manager.outgoing_connection.connection_fd,
           task->stream_manager.incoming_connection.connection_fd);
    pthread_mutex_lock(&task_queue_mutex);
    task_queue[task_queue_tail] = *task;
    task_queue_tail = (task_queue_tail + 1) % MAX_TASKS;
    pthread_cond_signal(&task_queue_cond); // Signal the tasks thread that a new task is available
    pthread_mutex_unlock(&task_queue_mutex);
}

// Dequeue a task to be processed by the tasks thread. This function will block if the queue is
// empty until a new task is enqueued.
Task dequeue_task()
{
    pthread_mutex_lock(&task_queue_mutex);
    while (task_queue_head == task_queue_tail)
    { // No tasks in the queue, wait for a task to be enqueued
        pthread_cond_wait(&task_queue_cond, &task_queue_mutex);
    }
    Task task = task_queue[task_queue_head];
    printf("[Task Manager] Dequeuing task with ID: %d\n", task.task_id);
    task_queue_head = (task_queue_head + 1) % MAX_TASKS;
    pthread_mutex_unlock(&task_queue_mutex);
    return task;
}

// Starts a new task and returns its ID. The task will be associated with a new stream manager for
// handling its data streams.
int prepare_task(Frame *frame, uint8_t server_fd, uint8_t client_fd)
{
    if (free_tasks == 0)
    {
        return -1; // No free task slots available
    }
    int index = free_task_slots[--free_tasks];
    Task *task = &tasks[index];
    task->status = TASK_STATUS_PREPARING;  // Mark as running
    task->function_id = frame->payload[0]; // First Byte determines called function ID

    task->input_data_len = frame->header.payload_len - 1; // Length of the input data
    task->input_data = malloc(task->input_data_len);
    (frame->payload[1]); // Other bytes are payload for the function

    StreamManager stream_manager = {.incoming_connection = {.stream_status = STREAM_STATUS_OPEN,
                                                            .connection_fd = server_fd,
                                                            .bytes_transferred = 0},
                                    .outgoing_connection = {.stream_status = STREAM_STATUS_OPEN,
                                                            .connection_fd = client_fd,
                                                            .bytes_transferred = 0}};

    task->stream_manager = stream_manager; // Associate the task with the provided stream
                                           // manager for handling its data streams
    printf("[Task] Task prepared with id %i\n", index);
    return index;
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

// Starts a task
int start_task(uint8_t task_id)
{
    Task *t = get_task_by_id(task_id);
    t->status = TASK_STATUS_RUNNING;
    enqueue_task(t); // Enqueue the task to be processed by the tasks thread
    printf("[Task] Started task with ID %i", task_id);
    return 0;
}
