#ifndef EMB_FUNC_H
#define EMB_FUNC_H

#include <stdint.h>

typedef struct
{
    uint32_t raw_data_len; // Length of the raw data
    uint8_t return_msg_id; // Message ID to use when sending the result back to the server
    void *raw_data;        // Result of the function execution
} ReturnValue;

typedef ReturnValue (*Func)(void *);

Func get_embedded_function_pointer(int function_id);

ReturnValue send_mirror_reply(void *arg);
ReturnValue func1(void *arg);

#endif