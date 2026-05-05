#include "embedded_functions.h"
#include "enums.h"
#include <stdio.h>
#include <string.h>

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id
Func function_table[] = {
    send_mirror_reply,
    func1,
};

ReturnValue execute_function(int function_id, void *arg)
{
    if (function_id < 0 || function_id >= sizeof(function_table) / sizeof(Func))
    {
        printf("Invalid function ID: %d\n", function_id);
        return (ReturnValue){0};
    }

    Func func = function_table[function_id];
    return func(arg); // Call the function
}

ReturnValue send_mirror_reply(void *arg)
{
    printf("send_mirror_reply called\n");

    return (ReturnValue){.raw_data = arg, .raw_data_len = strlen((char *)arg), .return_msg_id = RETURN};
}

ReturnValue func1(void *arg)
{
    printf("Function 1 executed\n");
    char *msg = "func1 called";
    return (ReturnValue){.raw_data = msg, .raw_data_len = strlen(msg), .return_msg_id = RETURN};
}