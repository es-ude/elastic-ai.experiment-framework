#include "embedded_functions.h"
#include "enums.h"
#include <stdio.h>
#include <string.h>

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id
static FuncMetadata function_table[] = {
    {.infinite_arguments = false,
     .amount_returns = 1,
     .argument_bytes_expected = 1024,
     .fnc_pointer = send_mirror_reply},
    {.argument_bytes_expected = 0,
     .amount_returns = 1,
     .fnc_pointer = func1}};

FuncMetadata *get_embedded_function(int function_id)
{
    if (function_id < 0 || function_id >= sizeof(function_table) / sizeof(Func))
    {
        printf("Invalid function ID: %d\n", function_id);
        return NULL;
    }
    return &function_table[function_id];
}

ReturnValue send_mirror_reply(void *arg)
{
    printf("send_mirror_reply called\n");

    return (ReturnValue){.raw_data = arg, .raw_data_len = strlen(arg), .return_msg_id = RETURN};
}

ReturnValue func1(void *arg)
{
    printf("Function 1 executed\n");
    char *msg = "func1 called";
    return (ReturnValue){.raw_data = msg, .raw_data_len = strlen(msg), .return_msg_id = RETURN};
}