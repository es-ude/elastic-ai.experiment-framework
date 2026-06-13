#include "transport.h"

#include <stdlib.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <stdio.h>
#include <pthread.h>
#include <errno.h>
#include <string.h>

typedef struct
{
    int listenfd;
    int clientfd;
} SocketImpl;

static pthread_t recv_thread;

static void *socket_receive_thread(void *t)
{
    Transport *transport = (Transport *)t;
    SocketImpl *s = (SocketImpl *)transport->impl;

    s->clientfd = -1;
    while (1)
    {
        // =========================
        // 1. WAIT FOR CONNECTION
        // =========================
        if (s->clientfd < 0)
        {
            s->clientfd = accept(s->listenfd, NULL, NULL);

            if (s->clientfd < 0)
            {
                perror("accept");
                sleep(1);
                continue;
            }

            printf("[Server] Client connected!\n");
        }

        // =========================
        // 2. RECEIVE LOOP
        // =========================
        uint8_t b;
        ssize_t n = recv(s->clientfd, &b, 1, 0);

        // printf("recv n=%ld errno=%d\n", n, errno);

        if (n > 0)
        {
            // printf("[Server] Received byte: 0x%02X\n", b);

            ringbuffer_push(transport->incoming_rb, &b);
            continue;
        }

        // =========================
        // 3. DISCONNECT HANDLING
        // =========================
        if (n == 0)
        {
            printf("[Server] Client disconnected\n");
        }
        else
        {
            printf("[Server] recv error: %s\n", strerror(errno));
        }

        close(s->clientfd);
        s->clientfd = -1;
    }

    return NULL;
}

static void socket_send(Transport *t, uint8_t b)
{
    SocketImpl *s = (SocketImpl *)t->impl;

    printf("[Server] Sending byte: 0x%02X\n", b);
    send(s->clientfd, &b, 1, 0);
}

static uint8_t socket_recv(Transport *t)
{
    uint8_t b = 0;
    SocketImpl *s = (SocketImpl *)t->impl;

    recv(s->clientfd, &b, 1, 0);
    return b;
}

static void socket_destroy(Transport *t)
{
    SocketImpl *s = (SocketImpl *)t->impl;

    close(s->clientfd);
    close(s->listenfd);

    pthread_cancel(recv_thread);
}

void transport_init(Transport *buf, TransportConfig cfg)
{
    Transport *t = buf;

    SocketImpl *s = (SocketImpl *)t->impl;

    s->listenfd = socket(AF_INET, SOCK_STREAM, 0);
    if (s->listenfd < 0)
    {
        perror("socket");
        return;
    }

    int opt = 1;
    setsockopt(s->listenfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(cfg.cfg.socket.port);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(s->listenfd, (struct sockaddr *)&addr, sizeof(addr)) < 0)
    {
        perror("bind");
        close(s->listenfd);
        return;
    }

    if (listen(s->listenfd, 1) < 0)
    {
        perror("listen");
        close(s->listenfd);
        return;
    }

    t->send_byte = socket_send;
    t->recv_byte = socket_recv;
    t->destroy = socket_destroy;

    t->incoming_rb = cfg.incoming_rb;
    if (pthread_create(&recv_thread, NULL, socket_receive_thread, t) != 0)
    {
        perror("pthread_create");
        close(s->listenfd);
        return;
    }
}

void transport_poll(Transport *transport)
{
}

uint64_t transport_get_current_time()
{
    time_t current_time;
    time(&current_time);

    return (uint64_t)current_time;
}