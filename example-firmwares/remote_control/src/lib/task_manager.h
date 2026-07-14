#ifndef TASK_MANAGER_H
#define TASK_MANAGER_H

#include "frame.h"
#include "task.h"
#include "ringbuffer.h"
#include <stdbool.h>

#define QUEUE_TASK_LEN 16

typedef struct
{
    Task task_pool[MAX_TASKS]; // Support up to MAX_TASKS concurrent tasks
    uint8_t free_tasks;

} TaskManager;

typedef struct
{
    uint32_t size;
    TaskDefinition *task_definitions;
} UserTasks;

void init_task_manager(RingBuffer *outgoing_rb, TaskManager *task_manager, TaskDefinition *task_definition_table, uint32_t task_definition_table_size);
void enqueue_task(RingBuffer *rb, Task *task);
// int prepare_task(Frame *frame, uint8_t server_fd, uint8_t client_fd);
Task *get_free_task(TaskManager *task_manager);
Task *get_task_by_id(uint8_t associated_transaction_id, TaskManager *task_manager);
bool start_task(RingBuffer *rb, Task *task);

bool init_task(Task *self, Frame *frame, TaskManager *task_manager);
bool finish_task(Task *task, TaskManager *task_manager);
bool send_frame_to_task(RingBuffer *task_rb, Task *task, Frame *frame);

void process_tasks(RingBuffer *task_rb, RingBuffer *outgoing_rb, TaskManager *task_manager);

TaskDefinition *get_task_definition(uint32_t task_definition_id);

#endif