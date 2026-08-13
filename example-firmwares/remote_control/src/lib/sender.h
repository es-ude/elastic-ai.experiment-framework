#ifndef SENDER_H
#define SENDER_H

#include "frame.h"
#include "ringbuffer.h"

#include "transport.h"
#include "task.h"

#include <stdbool.h>

#define UNACKED_MSG_MAX_AMOUNT 16
#define MAX_RETRY_COUNT 3
#define ACK_TIMEOUT_S 1

typedef enum
{
    STATE_FREE,
    STATE_SENT,
    STATE_ACKED,
    STATE_FAILED
} TxState;

typedef struct
{
    uint32_t seq;
    uint32_t last_sent_ms;
    uint8_t retry_count;
    TxState state;
    Frame frame;
    uint8_t used;
} AckTracker;

typedef struct
{
    Frame frame;
    uint8_t is_retransmit;
} OutgoingOrder;

typedef struct
{
    Transport *transport;
    enum
    {
        TX_IDLE,
        TX_SEND_START,
        TX_SEND_HEADER,
        TX_SEND_PAYLOAD,
        TX_SEND_CHECKSUM,
        TX_DONE
    } state;

    RingBuffer *outgoing_rb;

    Frame frame;
    uint16_t index;

    uint8_t is_retransmitting;

    AckTracker ack_trackers[UNACKED_MSG_MAX_AMOUNT];

    uint8_t msg_counter[MAX_TASKS];
} Sender;

void tx_process(Sender *tx);
void process_tx(Sender *tx);

void on_ack(Sender *tx, uint8_t acked_msg_id);
void on_nack(Sender *tx, uint8_t nacked_msg_id);

uint8_t send_return(TaskServices *task_s, uint8_t flags, uint32_t return_code, bool add_checksum);
uint8_t send_data(TaskServices *task_s, uint8_t flags, uint8_t *data, uint32_t data_len, bool add_checksum);

#endif