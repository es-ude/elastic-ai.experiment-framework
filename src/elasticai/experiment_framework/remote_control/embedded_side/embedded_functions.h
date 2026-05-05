#include <stdint.h>

typedef struct
{
    uint32_t raw_data_len; // Length of the raw data
    uint8_t return_msg_id; // Message ID to use when sending the result back to the server
    void *raw_data;        // Result of the function execution
} ReturnValue;

typedef ReturnValue (*Func)(void *);

ReturnValue execute_function(int function_id, void *arg);

ReturnValue send_mirror_reply(void *arg);
ReturnValue func1(void *arg);