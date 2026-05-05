#include <stdint.h>
#include "frame.h"
#include "sockets.h"
#include "task_manager.h"

typedef struct
{
    uint8_t fnc_id;
    char *message;
} cli_params;

int frame_builder_return(Frame *frame, uint8_t flags, uint8_t return_code, uint8_t task_id,
                         uint8_t caller_msg_id);

int msg_open_task(Frame *frame, Server server);
int msg_close_task(Frame *frame);
int msg_return(Frame *frame);
int msg_data_chunk(Frame *frame);

int handle_incoming_frame(Frame *frame, Server server, Frame *response);

void *server_thread(void *arg);
void *client_thread(void *arg);
void *sending_thread(void *arg);
void *tasks_thread(void *arg);
