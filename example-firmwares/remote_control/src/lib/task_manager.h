#ifndef TASK_MANAGER_H
#define TASK_MANAGER_H

#include "frame.h"
#include "task.h"
#include "ringbuffer.h"
#include <stdbool.h>

#define MAX_TASKS 32
#define QUEUE_TASK_LEN 16

typedef struct
{
    Task task_pool[MAX_TASKS]; // Support up to MAX_TASKS concurrent tasks
    uint8_t free_tasks;
    TaskContext ctx;
} TaskManager;

void init_tasks(RingBuffer *outgoing_rb);
void enqueue_task(RingBuffer *rb, Task *task);
Task *dequeue_task();
// int prepare_task(Frame *frame, uint8_t server_fd, uint8_t client_fd);
Task *get_free_task();
Task *get_task_by_id(uint8_t associated_transaction_id);
bool start_task(RingBuffer *rb, Task *task);

bool init_task(Task *self, Frame *frame);
bool finish_task(Task *task);
bool send_frame_to_task(RingBuffer *task_rb, Task *task, Frame *frame);

void process_tasks(RingBuffer *task_rb, RingBuffer *outgoing_rb);
#endif