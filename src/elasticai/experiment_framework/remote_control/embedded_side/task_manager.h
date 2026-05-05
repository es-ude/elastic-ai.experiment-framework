#include "frame.h"
#include <stdbool.h>
#include <stdint.h>

#define MAX_TASKS 32

typedef struct
{
    bool stream_status; // 0 for closed, 1 for open
    int connection_fd;  // Store the file descriptor for the connection

    uint32_t bytes_transferred;
} StreamChannel;

typedef struct
{
    StreamChannel incoming_connection;
    StreamChannel outgoing_connection;

} StreamManager;

typedef struct
{
    uint8_t task_id;
    uint8_t status; // 0 for idle, 1 for running
    uint8_t *input_data;
    uint32_t input_data_len;
    uint8_t *output_data;
    uint32_t output_data_len;
    int function_id; // ID of the function to execute for this task
    StreamManager stream_manager;
} Task;

void init_tasks();
void enqueue_task(Task *task);
Task dequeue_task();
int prepare_task(Frame *frame, uint8_t server_fd, uint8_t client_fd);
Task *get_task_by_id(uint8_t task_id);
int start_task(uint8_t task_id);