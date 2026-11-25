#include "task_manager.h"

#ifdef PLATFORM_PICO
#include "task_definitions_pico.h"
#endif

#include "task_definition_host.h"

#define TASK_DEFINITION_TABLE_ENTRY(psetup, phandle, pteardown) \
    {.setup = psetup, .handle = phandle, .tear_down = pteardown, .name = #phandle}

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id

TaskDefinition task_definition_table[] = {
    TASK_DEFINITION_TABLE_ENTRY(default_setup, send_mirror_reply, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(default_setup, func1, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(default_setup, request_ack_from_pc, default_teardown),
#ifdef PLATFORM_PICO
    TASK_DEFINITION_TABLE_ENTRY(fast_setup_hardware_init, hardware_init, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(fast_setup_fpga_power_on, fpga_power_on, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(fast_setup_fpga_power_off, fpga_power_off, default_teardown), // 5
    TASK_DEFINITION_TABLE_ENTRY(default_setup, write_to_flash_from_remote, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(fast_setup_read_skeleton_id, read_skeletion_id, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(default_setup, predict, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(default_setup, write_to_flash, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(default_setup, erase_fpga_flash, default_teardown), // 10
    TASK_DEFINITION_TABLE_ENTRY(default_setup, get_flash_ones, default_teardown),
    TASK_DEFINITION_TABLE_ENTRY(default_setup, get_task_names, default_teardown)
#endif
};

const size_t task_definition_table_size =
    sizeof(task_definition_table) / sizeof(task_definition_table[0]);