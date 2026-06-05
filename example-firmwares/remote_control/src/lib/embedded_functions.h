#ifndef EMB_FUNC_H
#define EMB_FUNC_H

#include <stdint.h>
#include <stdbool.h>

#include "task.h"

typedef void (*Func)(Task *task, TaskContext *ctx);

typedef struct
{
    Func fnc_pointer;
} FuncMetadata;

FuncMetadata *get_embedded_function(int function_id);

void send_mirror_reply(Task *task, TaskContext *ctx);
void func1(Task *task, TaskContext *ctx);

#endif