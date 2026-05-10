#include "sender.h"
#include "connection_manager.h"

#include <arpa/inet.h>
#include <stdio.h>

int msg_id = 0; // Global message ID counter for tracking messages

ThreadSafeQueue *outgoing_queue = NULL;

void init_sending_queue()
{
    outgoing_queue = queue_create(OUTGOING_QUEUE_SIZE, sizeof(SendOrder));
}

/* Send the frame over the socket */
int send_frame(int fd, Frame *frame)
{
    msg_id = (msg_id + 1) % 256;   // Increment global message ID for each sent message
    frame->header.msg_id = msg_id; // Assign the global message ID for tracking
    send(fd, &frame->header, FRAME_OVERHEAD,
         0);                                                // Send the header first (start_byte, message_type, flags, msg_id, payload_len)
    send(fd, frame->payload, frame->header.payload_len, 0); // Send the payload separately
    printf("\n");
    printf("[Sockets] Sent frame "
           "with header:\n Type: %d, Flags: %02X, Msg_id %02X, Payload Length: %d\n",
           frame->header.message_type, frame->header.flags, frame->header.msg_id, frame->header.payload_len);
    if (frame->header.payload_len > 0)
    {
        print_payload(frame->payload, frame->header.payload_len);
    }
    return 0; // Success
}

// Waits for send_orders to be queued and sends them
void *sending_thread(void *arg)
{
    while (1)
    {
        SendOrder send_order;
        queue_pop(outgoing_queue, &send_order); // Wait for a message to be enqueued by the server thread
        send_frame(send_order.fd, &(send_order.frame));
    }
    return NULL;
}
