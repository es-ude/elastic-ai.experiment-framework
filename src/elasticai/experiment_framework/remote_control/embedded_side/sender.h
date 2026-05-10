#ifndef SENDER_H
#define SENDER_H

#include "frame.h"
#include "ThreadSafeQueue.h"

#define OUTGOING_QUEUE_SIZE 16

typedef struct
{
    uint8_t fd;
    Frame frame;
} SendOrder;

extern ThreadSafeQueue *outgoing_queue;
void init_sending_queue();

int send_frame(int socket, Frame *frame);
void *sending_thread(void *arg);

#endif