#include "../../src/elasticai/experiment_framework/remote_control/embedded_side//sockets.h"
#include "../../src/elasticai/experiment_framework/remote_control/embedded_side/frame_builder.h"
#include "embedded_test.h"
#include <stdlib.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

int test_mirror_reply(Client client, cli_params *p)
{
    int test_result, chunks_generated, task_id;
    Frame open_task_frame, server_response, data_chunk_frame;
    SendOrder send_order;

    // Example send order 1. Open Task 2. receive Return with task_id 3. send Datachunk with text 4. Send empty Datachunk to confirm 5. receive Datachunk with text 6. receive return

    // step 1
    frame_builder_open_task(&open_task_frame, 0x00, p->fnc_id);

    send_order = (SendOrder){.fd = client.server_fd, .frame = open_task_frame};
    enqueue_message(&send_order);
    printf("Step 1\n");

    // step 2
    server_response = read_frame(client.server_fd); // Wait for a response from the server
    task_id = server_response.payload[1];           // this will be a return message so payload index 1
    printf("Step 2: Got Task Id %i\n", task_id);
    // step 3

    chunks_generated = frame_builder_data_chunk(&data_chunk_frame, 0x00, (uint8_t *)p->message, strlen(p->message), task_id, 0, 1024);
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
    if (strcmp((char *)data, p->message))
    {
        printf("[Test] Test failed. Sent \"%s\" and got \"%s\".\n", (char *)data, p->message);
        test_result = 1; // failure
    }
    else
    {
        printf("[Test] Test successful. Sent \"%s\" and got \"%s\".\n", (char *)data, p->message);
        test_result = 0; // correct
    }
    printf("Step 5\n");
    // step 6
    server_response = read_frame(client.server_fd); // Wait for a response from the server
    task_id = server_response.payload[1];           // this will be a return message so payload index
    printf("Step 6\n");

    return test_result;
}

void *client_thread(void *arg)
{
    Client client =
        start_client(8080); // Start the Client for sending responses and data back to the Host

    cli_params *p = (cli_params *)arg;

    int *result = malloc(sizeof(int));

    switch (p->fnc_id)
    {
    case 0:
        *result = test_mirror_reply(client, p);
    case 1:
        test_mirror_reply(client, p);
    }

    close_connection(client.server_fd);

    return result;
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

    void *return_value;
    pthread_join(client_t, &return_value);
    int *result = (int *)return_value;
    int result_value = *result;
    printf("Result: %d\n", result_value);

    free(result);
    return result_value;
}