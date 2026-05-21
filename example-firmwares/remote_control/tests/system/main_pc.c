#include <stdio.h>
#include <unistd.h>

#include "ringbuffer.h"
#include "task_manager.h"
#include "sender.h"
#include "receiver.h"

#define INCOMING_BUFFER_SIZE 16
#define OUTGOING_BUFFER_SIZE 16
#define TASK_BUFFER_SIZE 16

static RingBuffer incoming_rb;
static RingBuffer outgoing_rb;
static RingBuffer task_rb;

static Frame incoming_storage[INCOMING_BUFFER_SIZE];
static Frame outgoing_storage[OUTGOING_BUFFER_SIZE];
static Task *task_storage[TASK_BUFFER_SIZE];

static Receiver receiver;
static Sender sender;

void simulate_uart_input(void)
{
    static uint8_t stream[] =
        {
            0xAA, 0x01, 0x00, 0x03, 0x00, 0x03, 'A', 'B', 'C'};

    static int i = 0;

    if (i < sizeof(stream))
    {
        ringbuffer_push(&incoming_rb, &stream[i]);
        i++;
    }
}

void process_tx_pc(RingBuffer *rb, Sender *sender)
{
    Frame f;

    while (ringbuffer_pop(rb, &f))
    {
        printf("[TX] type=%d len=%d tx=%d\n",
               f.header.message_type,
               f.header.payload_len,
               f.header.transaction_id);
    }
}

int main(void)
{
    init_tasks();

    ringbuffer_init(&incoming_rb,
                    incoming_storage,
                    INCOMING_BUFFER_SIZE,
                    sizeof(Frame));

    ringbuffer_init(&outgoing_rb,
                    outgoing_storage,
                    OUTGOING_BUFFER_SIZE,
                    sizeof(Frame));

    ringbuffer_init(&task_rb,
                    task_storage,
                    TASK_BUFFER_SIZE,
                    sizeof(Task));

    while (1)
    {
        simulate_uart_input();

        process_rx(&receiver);

        process_tasks(&task_rb, &outgoing_rb);

        process_tx_pc(&outgoing_rb, &sender);

        usleep(1000);
    }

    return 0;
}