#include "receiver.h"
#include "connection_manager.h"
#include "sender.h"
#include "msg_handler.h"

#include <arpa/inet.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdio.h>

// Read a frame from the socket. This function will block until a complete frame is received (header
// + payload).
Frame read_frame(int fd)
{
    uint8_t header_buffer[FRAME_OVERHEAD] = {0};
    read(fd, header_buffer, FRAME_OVERHEAD); // Read the header first

    Frame frame = {.header = {.start_byte = header_buffer[0],
                              .message_type = header_buffer[1],
                              .flags = header_buffer[2],
                              .transaction_id = header_buffer[3],
                              .payload_len = header_buffer[4]},
                   .payload = NULL};

    if (frame.header.payload_len > 0)
    {
        frame.payload = malloc(frame.header.payload_len);
        read(fd, frame.payload, frame.header.payload_len); // Read the payload separately
    }

    return frame; // Success
}

// Handles incoming connections
void *receiving_thread(void *arg)
{

    

    ThreadArgs *args = (ThreadArgs *)arg;

    printf("host = %s\n", args->host);
    printf("port = %d\n", args->port);


    Server server = start_server(args->port);
    bool connected = false;

    Frame *framebuffer = malloc(sizeof(Frame));
    if (framebuffer == NULL)
    {
        perror("malloc failed");
        exit(1);
    }

    // Establish connection
    while (1)
    {
        printf("[Server] Waiting for Client to connect");
        server.client_fd = accept(server.server_fd, NULL, NULL); // Accept incoming connection on the server
        if (server.client_fd < 0)
        {
            perror("[Server] Failed to accept client connection");
            return NULL;
        }
        printf("[Server] Client connected.\n");
        connected = true;
        // Read messages
        while (connected)
        {
            printf("[Server] Waiting for new Message\n");
            Frame frame = read_frame(server.client_fd); // Read incoming frame from the server
            printf("[Server] Message Received");

            Frame response;

            int result = handle_incoming_frame(&frame, server, &response);
            switch (result)
            {
            case 0: // Do nothing
                break;
            case 1:                                                                                  // 1 means send a frame back
                queue_push(outgoing_queue, &(SendOrder){.fd = server.client_fd, .frame = response}); // Send the response back to the client
                break;
            case 2: // connection finished
                connected = false;
                break;
            default:
                printf("Error handling frame: %d\n", result);
                return NULL;
            }
        }
    }

    return NULL;
}