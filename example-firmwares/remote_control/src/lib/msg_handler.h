#include "frame.h"
#include "ringbuffer.h"
#include "task_manager.h"
#include "sender.h"

int msg_open_task(Frame *frame, TaskManager *task_manager, uint64_t *timer);
int msg_close_task(Frame *frame, TaskManager *task_manager);
int msg_return(Frame *frame);
int msg_data_chunk(RingBuffer *task_rb, Frame *frame, TaskManager *task_manager, uint64_t *timer);

void handle_incoming_frame(RingBuffer *task_rb, Frame *frame, TaskManager *task_manager, Sender *tx, uint64_t *timer);
