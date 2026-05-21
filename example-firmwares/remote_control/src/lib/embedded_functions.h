#ifndef EMB_FUNC_H
#define EMB_FUNC_H

#include <stdint.h>
#include <stdbool.h>

#include "task.h"

typedef void (*Func)(Task *task);

typedef struct
{
    Func fnc_pointer;
} FuncMetadata;

FuncMetadata *get_embedded_function(int function_id);

void send_mirror_reply(Task *task);
void func1(Task *task);

#endif