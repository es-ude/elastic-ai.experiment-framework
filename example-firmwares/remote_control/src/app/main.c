#include <stdio.h>
#include <unistd.h>

#include "ringbuffer.h"
#include "task_manager.h"
#include "sender.h"
#include "receiver.h"
#include "transport.h"

#define INCOMING_BUFFER_SIZE 128
#define OUTGOING_BUFFER_SIZE 16
#define TASK_BUFFER_SIZE 16

static volatile RingBuffer incoming_rb;
static RingBuffer outgoing_rb;
static RingBuffer task_rb;

static uint8_t incoming_storage[INCOMING_BUFFER_SIZE];
static Frame outgoing_storage[OUTGOING_BUFFER_SIZE];
static Task *task_storage[TASK_BUFFER_SIZE];

static Receiver receiver;
static Sender sender;

static Transport transport_protocol;

int main(void)
{
    ringbuffer_init(&incoming_rb, incoming_storage, INCOMING_BUFFER_SIZE, sizeof(uint8_t));
    ringbuffer_init(&outgoing_rb, outgoing_storage, OUTGOING_BUFFER_SIZE, sizeof(Frame));
    ringbuffer_init(&task_rb, task_storage, TASK_BUFFER_SIZE, sizeof(Task *));

    init_tasks(&outgoing_rb); // Initialize task manager with outgoing ring buffer for sending responses

    TransportConfig cfg = (TransportConfig){
        .type = TRANSPORT_SOCKET,
        .cfg.socket.port = 8080,
        .incoming_rb = &incoming_rb};
    transport_init(&transport_protocol, cfg);

    receiver = (Receiver){.incoming_rb = &incoming_rb,
                          .transport = &transport_protocol,
                          .task_rb = &task_rb};

    sender = (Sender){
        .transport = &transport_protocol,
        .outgoing_rb = &outgoing_rb};

    while (1)
    {
        process_rx(&receiver);

        process_tasks(&task_rb, &outgoing_rb);

        process_tx(&sender);
    }
}