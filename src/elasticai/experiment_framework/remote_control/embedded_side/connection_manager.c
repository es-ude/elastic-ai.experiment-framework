#include "connection_manager.h"
#include "enums.h"
#include "msg_handler.h"

#include <arpa/inet.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stddef.h>

// Start a TCP server
Server start_server(int port)
{
    printf("[Server] Starting server on port %i.\n", port);
    int server_fd, client_fd;
    struct sockaddr_in addr = {0};
    char buffer[1024] = {0};
    int result;

    do
    {
        server_fd = socket(AF_INET, SOCK_STREAM, 0);

        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(port);

        result = bind(server_fd, (struct sockaddr *)&addr, sizeof(addr));
        if (result < 0)
        {

            printf("[Server] bind failed on %i. retrying in 5 second\n", port);
            fflush(stdout);
            sleep(5);
            continue;
        }
    } while (result < 0);

    if (listen(server_fd, 3) < 0)
    {
        perror("[Server] Failed to listen on server socket");
        exit(EXIT_FAILURE);
    }

    printf("[Server] Server started. Listening on port %d...\n", ntohs(addr.sin_port));

    printf("[Server] Wait for connection...\n");

    Server server = {
        .server_fd = server_fd,
        .client_fd = -1};

    return server;
}

// Start a TCP client and connect to the server
Client start_client(int port)
{
    printf("[Client] Starting client...\n");
    int sock;
    struct sockaddr_in server_addr;
    char buffer[1024] = {0};

    sock = socket(AF_INET, SOCK_STREAM, 0);

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    inet_pton(AF_INET, "127.0.0.1", &server_addr.sin_addr);

    printf("[Client] Connecting to server...\n");
    while (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        printf("[Client] Failed to connect to server. Trying again in 1 second ...\n");
        sleep(1);
    }
    printf("[Client] Connected to server .\n");

    return (Client){.server_fd = sock};
}

void close_connection(int fd)
{
    close(fd);
}

void print_payload(uint8_t *payload, uint8_t payload_len)
{
    printf("[Payload] ");
    for (int i = 0; i < payload_len; i++)
    {
        printf("%02X ", payload[i]);
    }
    printf("\n\n");
}
