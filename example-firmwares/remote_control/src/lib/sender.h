#ifndef SENDER_H
#define SENDER_H

#include "frame.h"
#include "ringbuffer.h"

#include "transport.h"
#include "task.h"

typedef struct
{
    Transport *transport;
    enum
    {
        TX_IDLE,
        TX_SEND_START,
        TX_SEND_HEADER,
        TX_SEND_PAYLOAD,
        TX_DONE
    } state;

    RingBuffer *outgoing_rb;

    Frame frame;
    uint16_t index;

    uint8_t msg_counter[MAX_TASKS];
} Sender;

void tx_process(Sender *tx);
void process_tx(Sender *tx);

uint8_t send_return(TaskServices *task_s, uint8_t flags, uint32_t return_code);
uint8_t send_data(TaskServices *task_s, uint8_t flags, uint8_t *data, uint32_t data_len);

#endif