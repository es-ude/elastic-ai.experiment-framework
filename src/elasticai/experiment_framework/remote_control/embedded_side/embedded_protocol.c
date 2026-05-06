#include <arpa/inet.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "embedded_functions.h"
#include "embedded_protocol.h"
#include "enums.h"
#include "frame_builder.h"

int msg_open_task(Frame *frame, Server server)
{
    return prepare_task(frame, server.server_fd, server.client_fd);
}

int msg_close_task(Frame *frame)
{
    return -1; // Not implemented yet
}

int msg_return(Frame *frame)
{
    return -1; // Not implemented yet
}

// Handle incoming data chunk for a task. This will append the new chunk to the existing input data for the task
int msg_data_chunk(Frame *frame)
{
    printf("[Server] Handle incoming data chunk\n");
    Task *task = get_task_by_id(frame->payload[0]); // Get the task ID from the first byte of the payload to identify which task this data chunk belongs to
    printf("[Server] Fetched Task with id %i\n", task->task_id);
    if (task == NULL)
    {
        printf("Invalid task ID in data chunk: %d\n", frame->payload[0]);
        return -1; // Invalid task ID
    }

    // Check if the DATA_CHUNK has an empty Data_payload (task_id and data_id are still there, so 2 means empty)
    // if yes, then that means the end of a DATA_CHUNK Stream and the intention of starting the Task
    if (frame->header.payload_len == 2)
    {
        printf("Starting Task");
        task->stream_manager.incoming_connection.stream_status = STREAM_STATUS_CLOSED;
        int result = start_task(task->task_id); // Starts the task since it was the last Data_chunk
        return task->task_id;
    }

    // Append new data chunk to existing Data if it is not the last Data Chunk
    printf("Trying Realloc");
    fflush(stdout);
    uint8_t *tmp = realloc(task->input_data, task->input_data_len + frame->header.payload_len - 1); // Resize the input data buffer to accommodate the new chunk
    printf("realloc worked");
    fflush(stdout);

    if (tmp == NULL)
    {
        printf("Realloc failed");
        return -1;
    }
    task->input_data = tmp;

    memcpy(&(task->input_data[task->input_data_len]), &frame->payload[2], frame->header.payload_len - 1); // Copy the new chunk into the input data buffer
    task->input_data_len += frame->header.payload_len - 1;                                                // Update the input data length
    return task->task_id;
}

/*
 * Handles the frame interpreation.
 * @return Return code:
 *          0: no frame should be sent back
 *          1: send the "response" frame
 *          -1: error code
 */
int handle_incoming_frame(Frame *frame, Server server, Frame *response)
{
    int task_id;

    printf("\n[Server] Received frame \n Control Byte: %02X, Type: %02X, Flags: %02X, Msg ID: %02X, "
           "Payload Len: %d\n\n",
           frame->header.start_byte, frame->header.message_type, frame->header.flags,
           frame->header.msg_id, frame->header.payload_len);

    if (frame->header.start_byte != 0xAA)
    {
        printf("Invalid Start Byte");
        return -1; // Invalid start byte
    }

    printf("test");
    switch (frame->header.message_type)
    { // Start different tasks based on message type
    case OPEN_TASK:
        printf("[Server] Handling OPEN_TASK message.\n");

        task_id = msg_open_task(frame, server);

        // Create the frame for immediate return
        frame_builder_return(response, 0x00, (task_id >= 0) ? 0x00 : 0x01, task_id,
                             frame->header.msg_id); // Return success or failure code along with the
                                                    // task ID and caller message ID for tracking

        return 1; // Send return frame back
    case CLOSE_TASK:
        break;
    case RETURN:
        msg_return(frame);
        break;
    case DATA_CHUNK:
        printf("[Server] Handling DATA_CHUNK message");
        task_id = msg_data_chunk(frame);

        break;
    case ACK:
        break;
    case NACK:
        break;
    case HANDSHAKE:

        break;

    default:
        printf("Unknown message type: %02X\n", frame->header.message_type);
        return -2; // Unknown message type
    }

    return 0; // Success, no response needed
}

// Handles incoming connections
void *server_thread(void *arg)
{
    uint8_t header_buffer[FRAME_OVERHEAD] = {0};
    uint8_t payload_buffer[1024] = {0};

    Server server = start_server(8080); // Start the Server for receiving commands from the Host

    server.client_fd =
        accept(server.server_fd, NULL, NULL); // Accept incoming connection on the server
    if (server.client_fd < 0)
    {
        perror("[Server] Failed to accept client connection");
        return NULL;
    }

    printf("[Server] Client connected.\n");

    while (1)
    {
        printf("[Server] Waiting for new Message\n");
        Frame frame = read_frame(server.client_fd); // Read incoming frame from the server
        printf("[Server] Message Received");
        Frame response;
        int result = handle_incoming_frame(&frame, server, &response);

        if (result == 1)
        {
            enqueue_message(&(SendOrder){.fd = server.client_fd, .frame = response}); // Send the response back to the client
        }

        if (result < 0)
        {
            printf("Error handling frame: %d\n", result);
            return NULL;
        }
    }

    return NULL;
}

// Runs Tasks that were added to to task queue. Sends Reply messages if necessary
void *tasks_thread(void *arg)
{
    while (1)
    {
        Task task = dequeue_task(); // Wait for a task to be enqueued by the server thread when a
                                    // new OPEN_TASK message is received
        printf("Processing task with ID: %d\n", task.task_id);

        ReturnValue result = execute_function(
            task.function_id,
            task.input_data); // Execute the function associated with the task using its input data

        task.output_data = result.raw_data; // Store the result in the task's output data field
        task.output_data_len = result.raw_data_len;

        Frame response_frame;

        int msg_type = result.return_msg_id;
        switch (msg_type)
        {
        case RETURN:
            frame_builder_return(&response_frame, 0x00, 0x00, task.task_id,
                                 task.task_id);
        case DATA_CHUNK:
            frame_builder_data_chunk(&response_frame, 0x00, task.output_data, task.output_data_len, task.task_id, 0, 1024);
            enqueue_message(
                &(SendOrder){.fd = task.stream_manager.outgoing_connection.connection_fd,
                             .frame = response_frame}); // send Data first
            frame_builder_return(&response_frame, 0x00, 0x00, task.task_id,
                                 task.task_id); // send a return as last step
        }

        enqueue_message(
            &(SendOrder){.fd = task.stream_manager.outgoing_connection.connection_fd,
                         .frame = response_frame});
    }
    return NULL;
}

int main(int argc, char const *argv[])
{
    init_tasks(); // Initialize the task management system

    pthread_t server_t, sending_t, tasks_t;

    pthread_create(&server_t, NULL, server_thread, NULL);
    pthread_create(&sending_t, NULL, sending_thread, NULL);
    pthread_create(&tasks_t, NULL, tasks_thread, NULL);

    while (1)
    {
    }

    return 0;
}
