#include "transport.h"
#include <stdlib.h>

typedef struct
{
    int fd;
} UartImpl;

static void uart_send(Transport *t, uint8_t b)
{
    UartImpl *u = (UartImpl *)t->impl;
    (void)u;
    (void)b;
}

static uint8_t uart_recv(Transport *t)
{
    UartImpl *u = (UartImpl *)t->impl;
    (void)u;
    return 0;
}

static void uart_destroy(Transport *t)
{
}

void transport_init(Transport *buf, TransportConfig cfg)
{
    UartImpl *u = (UartImpl *)buf->impl;

    u->fd = 0; // uart_open(device, baud);

    buf->send_byte = uart_send;
    buf->recv_byte = uart_recv;
    buf->destroy = uart_destroy;
}

void transport_accept(Transport *t)
{
    (void)t;
    // uart_wait_for_connection(u->fd);
}