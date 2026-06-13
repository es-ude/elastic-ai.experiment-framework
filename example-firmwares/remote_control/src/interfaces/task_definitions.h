#pragma once

#include <stdint.h>
#include <stdbool.h>

#include "task.h"

typedef struct
{
    uint32_t size;
    TaskDefinition *task_definitions;
} UserTasks;

TaskDefinition *get_task_definition(uint32_t task_definition_id);