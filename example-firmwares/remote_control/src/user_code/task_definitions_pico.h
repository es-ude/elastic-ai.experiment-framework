#pragma once

#include "task.h"

void fast_setup_hardware_init(TaskContext *task_context);
void fast_setup_fpga_power_on(TaskContext *task_context);
void fast_setup_fpga_power_off(TaskContext *task_context);

void hardware_init(TaskContext *task_context);
void fpga_power_on(TaskContext *task_context);
void fpga_power_off(TaskContext *task_context);
void write_to_flash(TaskContext *task_context);
void write_to_flash_from_remote(TaskContext *task_context);
void read_skeletion_id(TaskContext *task_context);
void predict(TaskContext *task_context);