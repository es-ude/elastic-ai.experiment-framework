#include "../../src/elasticai/experiment_framework/remote_control/embedded_side/connection_manager.h"
#include "../../src/elasticai/experiment_framework/remote_control/embedded_side/frame_builder.h"
#include "../../src/elasticai/experiment_framework/remote_control/embedded_side/ThreadSafeQueue.h"
#include "../../src/elasticai/experiment_framework/remote_control/embedded_side/sender.h"
#include "../../src/elasticai/experiment_framework/remote_control/embedded_side/receiver.h"
#include "../../src/elasticai/experiment_framework/remote_control/embedded_side/task_manager.h"
#include <stdlib.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

typedef struct
{
    uint8_t fnc_id;
    char *message;
} cli_params;

int test_mirror_reply_v2(Client client, cli_params *p)
{
    // New Datachunk Payload Layout: Task_id data_id Payload_Size
    /*
     * 1. Send Open Task. Dont Expect return
     * 2. Send Configuration Datachunk with first Byte of Payload as total amount of Datachunks being sent. Rest of this is the Payload
     * 3. Receive Configuration Datachunk with first Byte of Payload as total amount of Datachunks being received. Rest is the payload
     * 4. Receive Return
     */
    int test_result, chunks_generated, associated_transaction_id;
    Frame open_task_frame, server_response, data_chunk_frame;
    SendOrder send_order;
    uint8_t flags = 0;

    // Step 1: Open Task
    frame_builder_open_task(&open_task_frame, 0, flags, p->fnc_id);
    send_order = (SendOrder){.fd = client.server_fd, .frame = open_task_frame};
    queue_push(outgoing_queue, &send_order);
    printf("Step 1:\n");
    fflush(stdout);
    // We assume a Task id of 0 here, since we started the server fresh

    // Step 2: Send parameter
    flags |= FLAG_START_TASK;
    frame_builder_data_chunk(&data_chunk_frame, flags, (uint8_t *)p->message, strlen(p->message), 0x0, 0, 1024);
    send_order = (SendOrder){.fd = client.server_fd, .frame = data_chunk_frame};
    queue_push(outgoing_queue, &send_order);
    printf("Step 2\n");
    fflush(stdout);
    // Step 3: Receive Config and Result

    server_response = read_frame(client.server_fd);
    print_payload(server_response.payload, server_response.header.payload_len);
    DataChunkPayload *casted_payload = (DataChunkPayload *)server_response.payload;

    uint8_t *response_data = casted_payload->payload; // Data Chunk with text as reply expected
    printf("[Client] Message Received: %s\n", (char *)response_data);

    if (strcmp((char *)response_data, p->message))
    {
        printf("[Test] Test failed. Sent \"%s\" and got \"%s\".\n", (char *)response_data, p->message);
        test_result = 1; // failure
    }
    else
    {
        printf("[Test] Test successful. Sent \"%s\" and got \"%s\".\n", (char *)response_data, p->message);
        test_result = 0; // correct
    }
    printf("Step 3\n");
    // Step 4: receive Return

    server_response = read_frame(client.server_fd);
    ReturnPayload *casted_return_payload = (ReturnPayload *)server_response.payload;

    int return_code = casted_return_payload->return_code;
    printf("Step 4: Got Return code %i\n", return_code);
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
        *result = test_mirror_reply_v2(client, p);
        break;
    case 1:
        test_mirror_reply_v2(client, p);
        break;
    }

    close_connection(client.server_fd);

    return result;
}

int main(int argc, char const *argv[])
{
    pthread_t client_t, sending_t;

    init_sending_queue();

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
    fflush(stdout);
    int result_value = *result;
    printf("Result: %d\n", result_value);

    free(result);
    return result_value;
}