#include <stdint.h>
#include "frame.h"
#include "sockets.h"
#include "task_manager.h"

int msg_open_task(Frame *frame, Server server);
int msg_close_task(Frame *frame);
int msg_return(Frame *frame);
int msg_data_chunk(Frame *frame);

int handle_incoming_frame(Frame *frame, Server server, Frame *response);

void *server_thread(void *arg);

void *tasks_thread(void *arg);
