#pragma once

#include <stdint.h>
#include <stddef.h>

typedef struct Transport Transport;

typedef struct
{
    enum
    {
        TRANSPORT_UART,
        TRANSPORT_SOCKET
    } type;

    union
    {
        struct
        {
            const char *device;
            int baudrate;
        } uart;

        struct
        {
            uint16_t port;
        } socket;
    } cfg;

} TransportConfig;

struct Transport
{
    void (*send_byte)(Transport *self, uint8_t b);
    uint8_t (*recv_byte)(Transport *self);
    void (*destroy)(Transport *self);

    uint8_t impl[32];
};

void transport_init(Transport *buf, TransportConfig cfg);
void transport_accept(Transport *t);