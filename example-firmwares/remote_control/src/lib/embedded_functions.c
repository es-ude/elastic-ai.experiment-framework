#include "embedded_functions.h"
#include "msg_types.h"

#include <stdio.h>
#include <string.h>

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id
static FuncMetadata function_table[] = {
    {.fnc_pointer = send_mirror_reply},
    {.fnc_pointer = func1}};

FuncMetadata *get_embedded_function(int function_id)
{
    if (function_id < 0 || function_id >= sizeof(function_table) / sizeof(FuncMetadata))
    {
        printf("Invalid function ID: %d\n", function_id);
        fflush(stdout);
        return NULL;
    }
    return &function_table[function_id];
}

void send_mirror_reply(Task *task)
{
    printf("send_mirror_reply called\n");
}

void func1(Task *task)
{
    printf("Function 1 executed\n");
    char *msg = "func1 called";
}