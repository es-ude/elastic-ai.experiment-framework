#include "../sockets.h"
#include "../frame_builder.h"
#include "embedded_test.h"
#include <stdlib.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

void *client_thread(void *arg)
{
    Client client =
        start_client(8080); // Start the Client for sending responses and data back to the Host

    cli_params *p = (cli_params *)arg;

    // Example send order 1. Open Task 2. receive Return with task_id 3. send Datachunk with text 4. Send empty Datachunk to confirm 5. receive Datachunk with text 6. receive return

    // step 1
    Frame open_task_frame;
    frame_builder_open_task(&open_task_frame, 0x00, p->fnc_id);

    SendOrder send_order = {.fd = client.server_fd, .frame = open_task_frame};
    enqueue_message(&send_order);
    printf("Step 1\n");

    // step 2
    Frame server_response = read_frame(client.server_fd); // Wait for a response from the server
    int task_id = server_response.payload[1];             // this will be a return message so payload index 1
    printf("Step 2: Got Task Id %i\n", task_id);
    // step 3
    Frame data_chunk_frame;

    int chunks_generated = frame_builder_data_chunk(&data_chunk_frame, 0x00, (uint8_t *)p->message, strlen(p->message), task_id, 0, 1024);
    send_order = (SendOrder){.fd = client.server_fd, .frame = data_chunk_frame};
    enqueue_message(&send_order);
    printf("Step 3\n");
    // step 4
    chunks_generated = frame_builder_data_chunk(&data_chunk_frame, 0x00, 0, 0, task_id, chunks_generated, 1024); // Chunks generated als start für data_id
    send_order = (SendOrder){.fd = client.server_fd, .frame = data_chunk_frame};
    enqueue_message(&send_order);
    printf("Step 4\n");

    // step 5
    server_response = read_frame(client.server_fd);
    print_payload(server_response.payload, server_response.header.payload_len);
    uint8_t *data = &server_response.payload[2]; // Data Chunk with text as reply expected
    printf("[Client] Message Received: %s\n", (char *)data);
    printf("Step 5\n");
    // step 6
    server_response = read_frame(client.server_fd); // Wait for a response from the server
    task_id = server_response.payload[1];           // this will be a return message so payload index
    printf("Step 6\n");

    while (1)
    {

        server_response = read_frame(client.server_fd); // Wait for a response from the server (this will block
                                                        // until a response is received)
        printf("[Client] Received response from server - Control Byte: %02X, Type: %02X, Flags: "
               "%02X, Msg ID: %02X, Payload Len: %d\n",
               server_response.header.start_byte, server_response.header.message_type,
               server_response.header.flags, server_response.header.msg_id,
               server_response.header.payload_len);
        print_payload(server_response.payload, server_response.header.payload_len);
    }

    return NULL;
}

int main(int argc, char const *argv[])
{
    pthread_t client_t, sending_t;

    pthread_create(&sending_t, NULL, sending_thread, NULL);

    // If there is a command-line argument, start the client thread to send a message to the server
    // (this is just for testing purposes)
    if (argc > 1)
    {

        cli_params *p = malloc(sizeof(cli_params));

        p->fnc_id = (uint8_t)strtol(argv[1], NULL, 10);
        p->message = (char *)argv[2];

        pthread_create(&client_t, NULL, client_thread, p);
    }

    while (1)
    {
    }
}