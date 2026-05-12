#include "task_manager.h"
#include "connection_manager.h"
#include "frame_builder.h"
#include "sender.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

ThreadSafeQueue *task_pointer_queue = NULL;

#define FIXED_PAYLOAD_SIZE 2

// Task pool
static Task tasks[MAX_TASKS]; // Support up to MAX_TASKS concurrent tasks
int free_tasks;

// Initialize the task management system by marking all task slots as free.
void init_tasks()
{
    for (int i = 0; i < MAX_TASKS; i++)
    {

        tasks[i].task_id = i;
        tasks[i].init = init;
        tasks[i].finish = finish;
        tasks[i].receive_datachunk = receive_datachunk;
        tasks[i].status = TASK_STATUS_IDLE; // Mark all tasks as idle
        tasks[i].input_data = malloc(INITIAL_TASK_INPUT_BUFFER_BYTES);
    }

    free_tasks = MAX_TASKS; // All tasks are initially free

    task_pointer_queue = queue_create(QUEUE_TASK_LEN, sizeof(Task *));
    ;
}

// Enqueue a task to be processed by the tasks thread. This function is thread-safe and can be
// called from any thread to queue a new task for execution.
void enqueue_task(Task *task)
{
    printf("[Task Manager] Enqueue task with values: \n task_id: %d, function_id: %d, stream_outgoing: %d, "
           "stream_incoming: %d\n",
           task->task_id, task->function_id, task->transaction.outgoing_connection.connection_fd,
           task->transaction.incoming_connection.connection_fd);
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

// Get one free task pointer. Does not reserve the Task already
Task *get_free_task()
{
    for (int i = 0; i < MAX_TASKS; i++)
    {
        if (tasks[i].status == TASK_STATUS_IDLE)
        {
            return &tasks[i];
        }
    }

    return NULL;
}

bool init(Task *self, Frame *frame, uint8_t incoming_fd, uint8_t outgoing_fd)
{

    OpenTaskPayload *open_task_payload = (OpenTaskPayload *)frame->payload;

    if (self->status != TASK_STATUS_IDLE)
    {
        return false; // Task already running
    }
    if (free_tasks == 0)
    {
        return false; // No free task slots available
    }

    free_tasks--;

    self->status = TASK_STATUS_PREPARING;          // Mark as running
    self->function_id = open_task_payload->fnc_id; // First Byte determines called function ID

    Transaction transaction = {.transacion_id = frame->header.transaction_id,
                               .incoming_connection = {.stream_status = STREAM_STATUS_OPEN,
                                                       .connection_fd = incoming_fd,
                                                       .bytes_transferred = 0},
                               .outgoing_connection = {.stream_status = STREAM_STATUS_OPEN,
                                                       .connection_fd = outgoing_fd,
                                                       .bytes_transferred = 0}};

    self->transaction = transaction;

    // Get the Function and its metadata
    self->fnc_meta = *get_embedded_function(self->function_id);

    self->missing_argument_bytes = self->fnc_meta.argument_bytes_expected;
    self->run = self->fnc_meta.fnc_pointer;

    printf("[Task] Task prepared with id %i and fnc_id %i\n", self->task_id, self->function_id);
}

// @return @param bool if further Datachunks are expected
bool receive_datachunk(Task *self, Frame *frame)
{
    DataChunkPayload *payload = (DataChunkPayload *)frame->payload;
    uint8_t incoming_payload_size = frame->header.payload_len - DATACHUNK_PAYLOAD_STATIC_SIZE;

    if (self->fnc_meta.infinite_arguments == false)
    {
        self->missing_argument_bytes -= incoming_payload_size;
    }

    if (self->input_data_len == 0) // First arrived Datachunk
    {
        self->input_data = malloc(incoming_payload_size);
    }
    else // Subsequent Datachunks
    {
        // Resize the input data buffer to accommodate the new chunk
        uint8_t *tmp = realloc(self->input_data, self->input_data_len + incoming_payload_size);
        if (tmp == NULL)
        {
            printf("Realloc failed");
            return false;
        }
        self->input_data = tmp;
    }

    // Copy the new chunk into the input data buffer
    uint8_t *buf = (uint8_t *)self->input_data;
    memcpy(
        &(buf[self->input_data_len]),
        payload->payload,
        incoming_payload_size);

    self->input_data_len += incoming_payload_size;

    printf("[Task] Task has data: ");
    print_payload(self->input_data, self->input_data_len);

    // Check if we should start the task
    if (frame->header.flags & FLAG_START_TASK)
    {
        self->transaction.incoming_connection.stream_status = STREAM_STATUS_CLOSED;
        int result = start_task(self); // Starts the task since it was the last Data_chunk
        return false;
    }
    return true;
}

// Frees the allocated Space for the Data of the Task and resets the values
bool finish(Task *self)
{
    self->status = TASK_STATUS_IDLE;
    self->function_id = 0;
    self->transaction = (Transaction){0};
    self->fnc_meta = (FuncMetadata){0};
    self->missing_argument_bytes = 0;

    free(self->input_data);
    self->input_data = NULL;
    self->input_data_len = 0;

    free(self->output_data);
    self->output_data = NULL;
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
    uint8_t flags = 0;

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

        flags |= FLAG_START_TASK; // For now only one Dataframe
        switch (msg_type)
        {
        case RETURN:
            frame_builder_return(&response_frame,
                                 0,
                                 0x00,
                                 task->transaction.transacion_id); // send a return as last step

        case DATA_CHUNK:
            frame_builder_data_chunk(&response_frame,
                                     flags,
                                     task->output_data,
                                     task->output_data_len,
                                     task->task_id, 0, 1024);

            queue_push(outgoing_queue,
                       &(SendOrder){.fd = task->transaction.outgoing_connection.connection_fd,
                                    .frame = response_frame});

            frame_builder_return(&response_frame,
                                 0,
                                 0x00,
                                 task->transaction.transacion_id); // send a return as last step
        }

        queue_push(outgoing_queue,
                   &(SendOrder){.fd = task->transaction.outgoing_connection.connection_fd,
                                .frame = response_frame});
    }
    return NULL;
}