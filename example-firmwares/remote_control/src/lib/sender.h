#ifndef SENDER_H
#define SENDER_H

#include "frame.h"
#include "ringbuffer.h"

#include "transport.h"

#define UNACKED_MSG_MAX_AMOUNT 16
#define MAX_RETRY_COUNT 3

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
} TxTracker;

static TxTracker tx_trackers[UNACKED_MSG_MAX_AMOUNT];

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

    Frame unacked_msgs[UNACKED_MSG_MAX_AMOUNT];
    uint8_t unacked_msg_ids[UNACKED_MSG_MAX_AMOUNT];
} Sender;

void tx_process(Sender *tx);
void process_tx(Sender *tx);

void on_ack(uint8_t transaction_id);
void on_nack(Sender *tx, uint8_t transaction_id);

#endif