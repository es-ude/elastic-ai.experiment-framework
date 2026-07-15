#include "task_manager.h"

#ifdef PLATFORM_PICO
#include "task_definitions_pico.h"
#endif

#include "task_definition_host.h"

// Contains the functions that should be callable from the client_protocol via execute_function,
// position determines function_id

TaskDefinition task_definition_table[] = {
    {.setup = default_setup,
     .tear_down = default_teardown,
     .handle = send_mirror_reply},
    {.setup = default_setup,
     .tear_down = default_teardown,
     .handle = func1},
    {.setup = default_setup,
     .handle = request_ack_from_pc,
     .tear_down = default_teardown}
#ifdef PLATFORM_PICO
    ,
    {.setup = fast_setup_hardware_init,
     .handle = hardware_init,
     .tear_down = default_teardown},
    {.setup = fast_setup_fpga_power_on,
     .handle = fpga_power_on,
     .tear_down = default_teardown},
    {.setup = fast_setup_fpga_power_off,
     .handle = fpga_power_off,
     .tear_down = default_teardown},
    {.setup = default_setup,
     .handle = write_to_flash_from_remote,
     .tear_down = default_teardown},
    {.setup = fast_setup_read_skeleton_id,
     .handle = read_skeletion_id,
     .tear_down = default_teardown},
    {.setup = default_setup,
     .handle = predict,
     .tear_down = default_teardown},
    {.setup = default_setup,
     .handle = write_to_flash,
     .tear_down = default_teardown},
    {.setup = default_setup,
     .handle = erase_fpga_flash,
     .tear_down = default_teardown},
    {.setup = default_setup,
     .handle = get_flash_ones,
     .tear_down = default_teardown}
#endif
};

const size_t task_definition_table_size =
    sizeof(task_definition_table) / sizeof(task_definition_table[0]);