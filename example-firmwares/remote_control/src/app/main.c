#include <stdio.h>
#include <unistd.h>

#include "ringbuffer.h"
#include "task_manager.h"
#include "sender.h"
#include "receiver.h"
#include "transport.h"
#include "task_definitions.h"

#define INCOMING_BUFFER_SIZE 128
#define OUTGOING_BUFFER_SIZE 16
#define TASK_BUFFER_SIZE 16

static RingBuffer incoming_rb;
static RingBuffer outgoing_rb;
static RingBuffer task_rb;

static uint8_t incoming_storage[INCOMING_BUFFER_SIZE];
static OutgoingOrder outgoing_storage[OUTGOING_BUFFER_SIZE];
static Task *task_storage[TASK_BUFFER_SIZE];

static Receiver receiver;
static Sender sender;

static Transport transport_protocol;

static TaskManager task_manager;

int main(int argc, char *argv[])
{

    ringbuffer_init(&incoming_rb, incoming_storage, INCOMING_BUFFER_SIZE, sizeof(uint8_t));
    ringbuffer_init(&outgoing_rb, outgoing_storage, OUTGOING_BUFFER_SIZE, sizeof(OutgoingOrder));
    ringbuffer_init(&task_rb, task_storage, TASK_BUFFER_SIZE, sizeof(Task *));

    init_task_manager(&outgoing_rb, &task_manager); // Initialize task manager with outgoing ring buffer for sending responses

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
        .outgoing_rb = &outgoing_rb,
        .msg_counter = {0}};

    while (1)
    {
        process_rx(&receiver, &task_manager, &sender);

        process_tasks(&task_rb, &outgoing_rb, &task_manager);

        process_tx(&sender);
    }
}