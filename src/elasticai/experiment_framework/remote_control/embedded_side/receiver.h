#ifndef RECEIVER_H
#define RECEIVER_H

#include "frame.h"

typedef struct
{
    const char *host;
    int port;
} ThreadArgs;

typedef struct
{
    uint8_t fd;
    Frame frame;
} ReceiveOrder;

Frame read_frame(int socket);
void *receiving_thread(void *arg);

#endif