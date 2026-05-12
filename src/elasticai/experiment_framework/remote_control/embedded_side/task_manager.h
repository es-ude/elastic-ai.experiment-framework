#ifndef TASK_MANAGER_H
#define TASK_MANAGER_H

#include "frame.h"
#include "ThreadSafeQueue.h"
#include "enums.h"
#include "embedded_functions.h"
#include <stdbool.h>
#include <stdint.h>

#define MAX_TASKS 32
#define QUEUE_TASK_LEN 16
#define INITIAL_TASK_INPUT_BUFFER_BYTES 1024

typedef struct
{
    bool stream_status; // 0 for closed, 1 for open
    int connection_fd;  // Store the file descriptor for the connection

    uint32_t bytes_transferred;
} StreamChannel;

typedef struct
{
    uint8_t transacion_id;
    StreamChannel incoming_connection;
    StreamChannel outgoing_connection;

} Transaction;

typedef struct Task Task;

struct Task
{
    uint8_t task_id;
    enum TaskStatus status; // 0 for idle, 1 for running

    void *input_data;
    uint32_t input_data_len;
    void *output_data;
    uint32_t output_data_len;

    Transaction transaction;

    int function_id; // ID of the function to execute for this task
    FuncMetadata fnc_meta;
    uint32_t missing_argument_bytes;

    bool (*init)(Task *self, Frame *frame, uint8_t incoming_fd, uint8_t outgoing_fd);
    ReturnValue (*run)(void *arg);
    bool (*receive_datachunk)(Task *self, Frame *frame);
    bool (*finish)(Task *self);
};

extern ThreadSafeQueue *task_pointer_queue;

void init_tasks();
void enqueue_task(Task *task);
Task *dequeue_task();
// int prepare_task(Frame *frame, uint8_t server_fd, uint8_t client_fd);
Task *get_free_task();
Task *get_task_by_id(uint8_t associated_transaction_id);
int start_task(Task *task);
void *tasks_thread(void *arg);

bool init(Task *self, Frame *frame, uint8_t incoming_fd, uint8_t outgoing_fd);
bool finish(Task *self);
bool receive_datachunk(Task *self, Frame *frame);

#endif