#ifndef CONNECTION_MANAGER_H
#define CONNECTION_MANAGER_H

#include <unistd.h>
#include <stdint.h>
#include "frame.h"

typedef struct
{
    int server_fd;
    int client_fd;
} Server;

typedef struct
{
    int server_fd;
} Client;

Server start_server(int port);
Client start_client(int port);

void close_connection(int fd);

void print_payload(uint8_t *payload, uint8_t payload_len);

#endif