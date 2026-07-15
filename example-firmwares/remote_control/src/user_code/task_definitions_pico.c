#include "task_definitions_pico.h"

#include "embedded_fpga_bitstream.h"
#include "hardware_functions/Middleware.h"
#include "config/config.h"
#include "eai/flash/Flash.h"
#include "hardware_functions/Fpga.h"

#include "eai/hal/EnV5HwConfiguration.h"
#include "eai/hal/EnV5HwController.h"
#include "pico/time.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define USER_LOGIC_START_ADDRESS 18
#define COMPUTE_BYTE 16

static void startCompute(void)
{
    uint8_t cmd[1] = {0x01};
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_write(fpga, cmd, COMPUTE_BYTE, 1);
}
static void stopCompute(void)
{
    uint8_t cmd[1] = {0x00};
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_write(fpga, cmd, COMPUTE_BYTE, 1);
}

static void eraseFlash(flashConfiguration_t *flashConfig, uint32_t startSector, uint32_t length)
{
    for (size_t index = 0;
         index <
         (size_t)ceilf((float)length / (float)flashGetBytesPerSector(flashConfig));
         index++)
    {
        flashEraseSector(flashConfig,
                         startSector + (index * flashGetBytesPerSector(flashConfig)));
    }
}

uint32_t flashWriteBitstream(
    flashConfiguration_t *flashConfig,
    const uint8_t *bitstream,
    uint32_t size)
{
    uint32_t written = 0;
    uint32_t address = 0;

    const uint32_t pageSize = flashConfig->bytesPerPage;

    // erase the flash before writing the bitstream with length of bitstream
    eraseFlash(flashConfig, 0, size);

    while (written < size)
    {
        uint32_t remaining = size - written;
        uint32_t bytesToWrite = remaining < pageSize ? remaining : pageSize;

        uint32_t result = flashWritePage(
            flashConfig,
            address,
            (uint8_t *)&bitstream[written],
            bytesToWrite);

        if (result != bytesToWrite)
        {
            printf("Flash write failed at address 0x%08lx\n", address);
            return written;
        }

        written += bytesToWrite;
        address += bytesToWrite;
    }

    return written;
}

uint32_t count_flash_ones(TaskContext *task_context, uint32_t length)
{
    data_t data_buffer = {0};
    data_buffer.length = length;

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&data_buffer.length, 4, false);
    uint32_t read_bytes = flashReadData(&flashConfig, 0, &data_buffer);
    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&read_bytes, 4, false);

    // simple id
    uint32_t ones = 0;

    for (size_t i = 0; i < data_buffer.length; i++)
    {
        uint8_t byte = data_buffer.data[i];

        for (int bit = 0; bit < 8; bit++)
        {
            ones += (byte >> bit) & 1;
        }
    }

    return ones;
}

// ---------------------------------------------------------------

void fast_setup_hardware_init(TaskContext *task_context)
{
    hardware_init(task_context);
}

void fast_setup_fpga_power_on(TaskContext *task_context)
{
    fpga_power_on(task_context);
}

void fast_setup_fpga_power_off(TaskContext *task_context)
{
    fpga_power_off(task_context);
}

void fast_setup_read_skeleton_id(TaskContext *task_context)
{
    read_skeletion_id(task_context);
}

// ---------------------------------------------------------------
void hardware_init(TaskContext *task_context)
{
    init_hardware();
    uint16_t value = flashConfig.bytesPerPage;

    uint8_t data[2] = {
        (uint8_t)(value >> 8),
        (uint8_t)(value & 0xFF)};

    task_context->task_services.send_data(&task_context->task_services, 0, data, 2, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void fpga_power_on(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();
    Fpga_powerOn(fpga);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void fpga_power_off(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();
    Fpga_powerOff(fpga);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void erase_fpga_flash(TaskContext *task_context)
{
    init_hardware();
    uint32_t amount_to_delete = 550000;
    eraseFlash(&flashConfig, 0, amount_to_delete);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void write_to_flash(TaskContext *task_context)
{
    init_hardware();
    uint32_t writtenBytes = flashWriteBitstream(&flashConfig, (uint8_t *)&fpga_bitstream, fpga_bitstream_size);
    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&writtenBytes, 4, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

typedef struct
{
    uint8_t target_sector;
    uint32_t written_bytes;
} UserDataStruct;

void write_to_flash_from_remote(TaskContext *task_context)
{
    if (task_context->step_counter > 0 && task_context->input_data_len < flashConfig.bytesPerPage)
    {
        // sending completed
        UserDataStruct *user_data = (UserDataStruct *)task_context->user_data;
        task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&user_data->written_bytes, 4, false);
        task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
        return;
    }

    if (task_context->step_counter == 0)
    {
        task_context->user_data = malloc(sizeof(UserDataStruct));
        UserDataStruct *user_data = (UserDataStruct *)task_context->user_data;
        user_data->written_bytes = 0;

        user_data->target_sector = task_context->input_data[0];

        eraseFlash(&flashConfig, 0, task_context->input_data_len);
    }
    else
    {
        UserDataStruct *user_data = (UserDataStruct *)task_context->user_data;
        uint16_t writtenBytes = flashWritePage(&flashConfig, (task_context->step_counter - 1) * flashConfig.bytesPerPage + (user_data->target_sector * flashConfig.bytesPerSector), task_context->input_data, flashConfig.bytesPerPage);
        user_data->written_bytes += writtenBytes;
    }

    task_context->input_data_len = 0; // set back to zero so new data overwrites old data
    task_context->step_counter++;

    // task_context->task_services.send_return(&task_context->task_services, 0, writtenBytes, false);
    return;
}

#define ADDR_MODEL_ID 0
#define BYTES_MODEL_ID 16

void read_skeletion_id(TaskContext *task_context)
{
    uint8_t skeleton_id[16] = {0};
    init_hardware();
    Fpga *fpga = Config_getFpga();
    if (!Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOn(fpga);
        sleep_ms(100); // wait for FPGA to power up
    }
    FpgaMiddleware *fpga_middleware = Config_getFpgaMiddleware();
    FpgaMiddleware_init(fpga_middleware);
    FpgaMiddleware_enableUserLogic(fpga_middleware);
    FpgaMiddleware_read(fpga_middleware, skeleton_id, ADDR_MODEL_ID, BYTES_MODEL_ID);
    FpgaMiddleware_disableUserLogic(fpga_middleware);
    FpgaMiddleware_deinit(fpga_middleware);

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&skeleton_id, BYTES_MODEL_ID, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void predict(TaskContext *task_context)
{

    // task_context->task_services.send_data(&task_context->task_services, 0, task_context->input_data, 1, false);
    // return;
    Fpga *fpga = Config_getFpga();
    if (!Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOn(fpga);
        sleep_ms(100); // wait for FPGA to power up
        char *msg = "power_fpga";
        task_context->task_services.send_data(&task_context->task_services, 0, msg, 10, false);
    }
    FpgaMiddleware *fpga_middleware = Config_getFpgaMiddleware();
    FpgaMiddleware_init(fpga_middleware);
    FpgaMiddleware_enableUserLogic(fpga_middleware);

    uint8_t result_size = task_context->input_data[0];
    uint8_t model_inference_input = task_context->input_data[1];

    FpgaMiddleware_write(fpga_middleware, &model_inference_input, USER_LOGIC_START_ADDRESS, 1);

    startCompute();
    while (FpgaMiddleware_fpgaIsBusy(fpga_middleware))
    {
    }
    stopCompute();

    FpgaMiddleware_read(fpga_middleware, task_context->output_data, USER_LOGIC_START_ADDRESS, result_size);
    task_context->output_data_len = task_context->input_data_len;

    FpgaMiddleware_disableUserLogic(fpga_middleware);
    FpgaMiddleware_deinit(fpga_middleware);

    task_context->task_services.send_data(&task_context->task_services, 0, task_context->output_data, result_size, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void get_flash_ones(TaskContext *task_context)
{
    init_hardware();
    uint32_t ones = count_flash_ones(task_context, 1024);

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&ones, 4, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}