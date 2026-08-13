#pragma once
#include "task.h"

void send_mirror_reply(TaskContext *task_context);
void func1(TaskContext *task_context);
void request_ack_from_pc(TaskContext *task_context);
void default_setup(TaskContext *task_context);
void fast_setup_ack_from_pc(TaskContext *task_context);
void default_teardown(TaskContext *task_context);