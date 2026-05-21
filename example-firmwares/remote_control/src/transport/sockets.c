#include "transport.h"

#include <stdlib.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <stdio.h>

typedef struct
{
    int listenfd;
    int clientfd;
} SocketImpl;

static void socket_send(Transport *t, uint8_t b)
{
    SocketImpl *s = (SocketImpl *)t->impl;
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
}

void transport_accept(Transport *t)
{
    SocketImpl *s = (SocketImpl *)t->impl;
    s->clientfd = accept(s->listenfd, NULL, NULL);
    if (s->clientfd < 0)
    {
        perror("accept");
        close(s->listenfd);
        return;
    }
    printf("connected clientfd = %d\n", s->clientfd);
}