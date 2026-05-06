#include "sockets.h"
#include <arpa/inet.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

int msg_id = 0; // Global message ID counter for tracking messages

#define OUTGOING_QUEUE_SIZE 16

// Outgoing messages being read by sending thread
SendOrder sending_queue[OUTGOING_QUEUE_SIZE];
int sending_queue_head = 0, sending_queue_tail = 0;

pthread_mutex_t sending_queue_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t sending_queue_cond = PTHREAD_COND_INITIALIZER;

// Start a TCP server
Server start_server(int port)
{
    printf("[Server] Starting server...\n");
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
            perror("[Server] bind failed. retrying in 1 second");
            sleep(1);
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

    Server server = {.server_fd = server_fd, .client_fd = -1};

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

// Enqueue a message to be sent by the sending thread. This function is thread-safe and can be
// called from any thread to send a message to the server.
void enqueue_message(SendOrder *order)
{
    // printf("[Sockets] Enqueuing message with ID: %d\n", order->frame.header.msg_id);
    pthread_mutex_lock(&sending_queue_mutex);
    sending_queue[sending_queue_tail] = *order;
    sending_queue_tail = (sending_queue_tail + 1) % OUTGOING_QUEUE_SIZE;
    pthread_cond_signal(
        &sending_queue_cond); // Signal the sending thread that a new message is available
    pthread_mutex_unlock(&sending_queue_mutex);
}

// Dequeue a message to be sent by the sending thread. This function will block if the queue is
// empty until a new message is enqueued.
SendOrder dequeue_message()
{
    pthread_mutex_lock(&sending_queue_mutex);
    while (sending_queue_head ==
           sending_queue_tail)
    { // Queue is empty, wait for a message to be enqueued
        pthread_cond_wait(&sending_queue_cond, &sending_queue_mutex);
    }
    SendOrder order = sending_queue[sending_queue_head];
    // printf("[Sockets] Dequeued message with ID: %d\n", order.frame.header.msg_id);
    sending_queue_head = (sending_queue_head + 1) % OUTGOING_QUEUE_SIZE;
    pthread_mutex_unlock(&sending_queue_mutex);
    return order;
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

/* Send the frame over the socket */
int send_frame(int fd, Frame *frame)
{
    msg_id = (msg_id + 1) % 256;   // Increment global message ID for each sent message
    frame->header.msg_id = msg_id; // Assign the global message ID for tracking
    send(fd, &frame->header, FRAME_OVERHEAD,
         0);                                                // Send the header first (start_byte, message_type, flags, msg_id, payload_len)
    send(fd, frame->payload, frame->header.payload_len, 0); // Send the payload separately
    printf("\n");
    printf("[Sockets] Sent frame "
           "with header:\n ID: %d, Type: %02X, Flags %02X, Payload Length: %d\n",
           frame->header.msg_id, frame->header.message_type, frame->header.flags, frame->header.payload_len);
    if (frame->header.payload_len > 0)
    {
        print_payload(frame->payload, frame->header.payload_len);
    }
    return 0; // Success
}

// Read a frame from the socket. This function will block until a complete frame is received (header
// + payload).
Frame read_frame(int fd)
{
    uint8_t header_buffer[FRAME_OVERHEAD] = {0};
    read(fd, header_buffer, FRAME_OVERHEAD); // Read the header first

    Frame frame = {.header = {.start_byte = header_buffer[0],
                              .message_type = header_buffer[1],
                              .flags = header_buffer[2],
                              .msg_id = header_buffer[3],
                              .payload_len = header_buffer[4]},
                   .payload = NULL};

    if (frame.header.payload_len > 0)
    {
        frame.payload = malloc(frame.header.payload_len);
        read(fd, frame.payload, frame.header.payload_len); // Read the payload separately
    }

    return frame; // Success
}

// Waits for send_orders to be queued and sends them
void *sending_thread(void *arg)
{
    while (1)
    {
        SendOrder send_order = dequeue_message(); // Wait for a message to be enqueued by the server thread
        send_frame(send_order.fd, &(send_order.frame));
    }
    return NULL;
}