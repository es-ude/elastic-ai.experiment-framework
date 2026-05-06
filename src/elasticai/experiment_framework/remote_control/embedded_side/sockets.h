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

void enqueue_message(SendOrder *order);
SendOrder dequeue_message();

void print_payload(uint8_t *payload, uint8_t payload_len);

int send_frame(int socket, Frame *frame);
Frame read_frame(int socket);

void *sending_thread(void *arg);
