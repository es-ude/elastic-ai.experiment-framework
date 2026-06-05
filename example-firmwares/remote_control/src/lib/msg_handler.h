#include "frame.h"
#include "ringbuffer.h"
#include "sender.h"

int msg_open_task(Frame *frame);
int msg_close_task(Frame *frame);
int msg_return(Frame *frame);
int msg_data_chunk(RingBuffer *task_rb, Frame *frame);

void handle_incoming_frame(RingBuffer *task_rb, Frame *frame, Sender *tx);