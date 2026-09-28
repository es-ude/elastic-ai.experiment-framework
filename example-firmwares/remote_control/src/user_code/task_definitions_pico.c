#include "task_definitions_pico.h"

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
#include <string.h>
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

typedef struct
{
    uint64_t timer;
    void *further_user_data;
} TimerUserDataStruct;

typedef struct
{
    uint8_t target_sector;
    uint32_t written_bytes;
} UserDataStruct;

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

void setup_start_timer(TaskContext *task_context)
{
    task_context->user_data = malloc(sizeof(TimerUserDataStruct));
    TimerUserDataStruct *timer = (TimerUserDataStruct *)task_context->user_data;

    uint64_t start_time = time_us_64();
    timer->timer = start_time;
}

// Function sends the timer since function start and sends a return. Should be called last. Needs user_data to be of type TimeUserDataStruct
void send_timer_return(TaskContext *task_context)
{
    uint64_t current_time = time_us_64();
    TimerUserDataStruct *timer = (TimerUserDataStruct *)task_context->user_data;

    uint64_t time_since_start = current_time - timer->timer;

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&time_since_start, 4, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

// ---------------------------------------------------------------

void timer_check(TaskContext *task_context)
{
    send_timer_return(task_context);
}

void timer_string_echo(TaskContext *task_context)
{
    task_context->task_services.send_data(&task_context->task_services, 0, task_context->input_data, task_context->input_data_len, false);
    send_timer_return(task_context);
}

void timer_fpga_power_on(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();
    Fpga_powerOn(fpga);
    send_timer_return(task_context);
}

void timer_write_to_flash_from_remote(TaskContext *task_context)
{
    if (task_context->step_counter > 0 && task_context->input_data_len < flashConfig.bytesPerPage)
    {
        // sending completed
        UserDataStruct *user_data = (UserDataStruct *)((TimerUserDataStruct *)task_context->user_data)->further_user_data;
        task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&user_data->written_bytes, 4, false);
        send_timer_return(task_context);
        return;
    }

    if (task_context->step_counter == 0)
    {
        ((TimerUserDataStruct *)task_context->user_data)->further_user_data = malloc(sizeof(UserDataStruct));
        UserDataStruct *user_data = (UserDataStruct *)((TimerUserDataStruct *)task_context->user_data)->further_user_data;
        user_data->written_bytes = 0;

        user_data->target_sector = task_context->input_data[0];

        eraseFlash(&flashConfig, 0, task_context->input_data_len);
    }
    else
    {
        UserDataStruct *user_data = (UserDataStruct *)((TimerUserDataStruct *)task_context->user_data)->further_user_data;
        uint16_t writtenBytes = flashWritePage(&flashConfig, (task_context->step_counter - 1) * flashConfig.bytesPerPage + (user_data->target_sector * flashConfig.bytesPerSector), task_context->input_data, flashConfig.bytesPerPage);
        if (writtenBytes <= 0)
        {
            char *error_msg = "Flash write failed";
            task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&error_msg, strlen(error_msg), false);
        }
        user_data->written_bytes += writtenBytes;
    }

    task_context->input_data_len = 0; // set back to zero so new data overwrites old data
    task_context->step_counter++;
}

void timer_predict(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();
    if (!Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOn(fpga);
        sleep_ms(100); // wait for FPGA to power up
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
    send_timer_return(task_context);
}

// ----------------------------------------------------------------------

void hardware_init(TaskContext *task_context)
{
    if (flashConfig.spiConfiguration->spiInstance == NULL)
    {
        init_hardware();
    }

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
    if (flashConfig.spiConfiguration->spiInstance == NULL)
    {
        init_hardware();
    }
    uint32_t amount_to_delete = 550000;
    eraseFlash(&flashConfig, 0, amount_to_delete);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

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
        Fpga *fpga = Config_getFpga();
        if (Fpga_isPoweredOn(fpga))
        {
            Fpga_powerOff(fpga);
        }

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
        if (writtenBytes <= 0)
        {
            char *error_msg = "Flash write failed";
            task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&error_msg, strlen(error_msg), false);
        }
        user_data->written_bytes += writtenBytes;
    }

    task_context->input_data_len = 0; // set back to zero so new data overwrites old data
    task_context->step_counter++;
}

#define ADDR_MODEL_ID 0
#define BYTES_MODEL_ID 16

void read_skeletion_id(TaskContext *task_context)
{
    uint8_t skeleton_id[16] = {0};
    if (flashConfig.spiConfiguration->spiInstance == NULL)
    {
        init_hardware();
    }
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
        while (!Fpga_isPoweredOn(fpga))
        {
            sleep_ms(1); // wait for FPGA to power up
        }
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
    if (flashConfig.spiConfiguration->spiInstance == NULL)
    {
        init_hardware();
    }
    uint32_t ones = count_flash_ones(task_context, 1024);

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&ones, 4, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

/* ============================================================
 * FPGA POWER ON
 * ============================================================ */

void fpga_power_on_core(Fpga *fpga)
{
    Fpga_powerOn(fpga);
}

/*
 * Normal remote task.
 *
 * No local timing is performed here.
 */
void p_fpga_power_on(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();

    fpga_power_on_core(fpga);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}

/*
 * Direct benchmark.
 *
 * Only the FPGA power-on operation is timed.
 * Protocol communication happens after the timer has stopped.
 */
void benchmark_fpga_power_on(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();

    uint64_t start = time_us_64();

    fpga_power_on_core(fpga);

    uint64_t elapsed = time_us_64() - start;

    /* data_id = 0 -> execution time */
    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        (uint8_t *)&elapsed,
        sizeof(elapsed),
        false);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}

/* ============================================================
 * ECHO
 * ============================================================ */

void echo_core(
    const uint8_t *input,
    uint16_t input_len,
    uint8_t *output)
{
    memcpy(output, input, input_len);
}

/*
 * Normal remote task.
 *
 * Receives the input through the task context and returns
 * the echoed data.
 */
void p_echo(TaskContext *task_context)
{
    echo_core(
        task_context->input_data,
        task_context->input_data_len,
        task_context->output_data);

    task_context->output_data_len =
        task_context->input_data_len;

    /* data_id = 0 -> echo result */
    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        task_context->output_data,
        task_context->output_data_len,
        false);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}

/*
 * Direct benchmark.
 *
 * The memcpy operation itself is timed.
 * Sending the timing result and echo result happens afterwards.
 */
void benchmark_echo(TaskContext *task_context)
{
    uint8_t input[256];
    uint8_t output[256];

    memset(input, 0, sizeof(input));

    uint64_t start = time_us_64();

    echo_core(
        input,
        sizeof(input),
        output);

    uint64_t elapsed = time_us_64() - start;

    /* data_id = 0 -> execution time */
    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        (uint8_t *)&elapsed,
        sizeof(elapsed),
        false);

    /* data_id = 1 -> echo result */
    task_context->task_services.send_data(
        &task_context->task_services,
        1,
        output,
        sizeof(output),
        false);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}

/* ============================================================
 * PREDICT
 * ============================================================ */

void predict_core(
    Fpga *fpga,
    FpgaMiddleware *fpga_middleware,
    const uint8_t *input,
    uint8_t input_len,
    uint8_t *output,
    uint8_t *output_len)
{
    (void)input_len;

    if (!Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOn(fpga);

        while (!Fpga_isPoweredOn(fpga))
        {
            sleep_ms(1);
        }
    }

    FpgaMiddleware_init(fpga_middleware);
    FpgaMiddleware_enableUserLogic(fpga_middleware);

    uint8_t result_size = input[0];
    uint8_t model_inference_input = input[1];

    FpgaMiddleware_write(
        fpga_middleware,
        &model_inference_input,
        USER_LOGIC_START_ADDRESS,
        1);

    startCompute();

    while (FpgaMiddleware_fpgaIsBusy(fpga_middleware))
    {
    }

    stopCompute();

    FpgaMiddleware_read(
        fpga_middleware,
        output,
        USER_LOGIC_START_ADDRESS,
        result_size);

    *output_len = result_size;

    FpgaMiddleware_disableUserLogic(fpga_middleware);
    FpgaMiddleware_deinit(fpga_middleware);
}

/*
 * Normal remote task.
 *
 * No local timing is performed here.
 */
void p_predict(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();

    FpgaMiddleware *fpga_middleware =
        Config_getFpgaMiddleware();

    uint8_t output_len;

    predict_core(
        fpga,
        fpga_middleware,
        task_context->input_data,
        task_context->input_data_len,
        task_context->output_data,
        &output_len);

    task_context->output_data_len = output_len;

    /* data_id = 0 -> prediction result */
    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        task_context->output_data,
        task_context->output_data_len,
        false);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}

/*
 * Direct benchmark.
 *
 * The complete predict_core() execution is timed.
 * Protocol communication happens after the timer has stopped.
 */
void benchmark_predict(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();

    FpgaMiddleware *fpga_middleware =
        Config_getFpgaMiddleware();

    uint8_t output[16];
    uint8_t output_len;

    /*
     * Use exactly the input received through the DATA_CHUNK.
     *
     * input[0] = result size
     * input[1] = model inference input
     */
    if (task_context->input_data_len != 2)
    {
        task_context->task_services.send_return(
            &task_context->task_services,
            1,
            0,
            false);
        return;
    }

    uint64_t start = time_us_64();

    predict_core(
        fpga,
        fpga_middleware,
        task_context->input_data,
        task_context->input_data_len,
        output,
        &output_len);

    uint64_t elapsed = time_us_64() - start;

    /* data_id = 0 -> execution time */
    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        (uint8_t *)&elapsed,
        sizeof(elapsed),
        false);

    /* data_id = 1 -> prediction result */
    task_context->task_services.send_data(
        &task_context->task_services,
        1,
        output,
        output_len,
        false);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}

extern const uint8_t _binary_env5_top_reconfig_bin_start[];
extern const uint8_t _binary_env5_top_reconfig_bin_end[];

/* ============================================================
 * FLASH WRITE
 * ============================================================ */

void flash_write_begin_core(
    uint8_t target_sector,
    uint16_t input_len)
{
    (void)target_sector;

    Fpga *fpga = Config_getFpga();

    if (Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOff(fpga);
    }

    eraseFlash(
        &flashConfig,
        0,
        input_len);
}

uint16_t flash_write_page_core(
    uint8_t target_sector,
    uint32_t page_index,
    const uint8_t *data)
{
    uint32_t address =
        page_index * flashConfig.bytesPerPage + target_sector * flashConfig.bytesPerSector;

    return flashWritePage(
        &flashConfig,
        address,
        (uint8_t *)data,
        flashConfig.bytesPerPage);
}

void p_write_to_flash_from_remote(TaskContext *task_context)
{
    if (
        task_context->step_counter > 0 &&
        task_context->input_data_len < flashConfig.bytesPerPage)
    {
        UserDataStruct *user_data =
            (UserDataStruct *)task_context->user_data;

        task_context->task_services.send_data(
            &task_context->task_services,
            0,
            (uint8_t *)&user_data->written_bytes,
            sizeof(user_data->written_bytes),
            false);

        task_context->task_services.send_return(
            &task_context->task_services,
            0,
            0,
            false);

        return;
    }

    if (task_context->step_counter == 0)
    {
        task_context->user_data =
            malloc(sizeof(UserDataStruct));

        if (task_context->user_data == NULL)
        {
            task_context->task_services.send_return(
                &task_context->task_services,
                1,
                0,
                false);

            return;
        }

        UserDataStruct *user_data =
            (UserDataStruct *)task_context->user_data;

        user_data->written_bytes = 0;
        user_data->target_sector =
            task_context->input_data[0];

        flash_write_begin_core(
            user_data->target_sector,
            task_context->input_data_len);
    }
    else
    {
        UserDataStruct *user_data =
            (UserDataStruct *)task_context->user_data;

        uint16_t written_bytes =
            flash_write_page_core(
                user_data->target_sector,
                task_context->step_counter - 1,
                task_context->input_data);

        user_data->written_bytes += written_bytes;
    }

    task_context->input_data_len = 0;
    task_context->step_counter++;
}

void benchmark_flash_write(TaskContext *task_context)
{
    if (task_context->input_data_len != 1)
    {
        task_context->task_services.send_return(
            &task_context->task_services,
            1,
            0,
            false
        );
        return;
    }

    if (flashConfig.spiConfiguration->spiInstance == NULL)
    {
        init_hardware();
    }

    uint8_t target_sector = task_context->input_data[0];

    const uint8_t *bitstream =
        _binary_env5_top_reconfig_bin_start;

    uint32_t size =
        (uint32_t)(
            _binary_env5_top_reconfig_bin_end
            - _binary_env5_top_reconfig_bin_start
        );

    Fpga *fpga = Config_getFpga();

    if (Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOff(fpga);
    }

    uint64_t start = time_us_64();

    eraseFlash(&flashConfig, 0, 550000);
    
    uint32_t written = 0;
    uint32_t page_size = flashConfig.bytesPerPage;
    uint32_t base_address =
        target_sector * flashConfig.bytesPerSector;

    while (written + page_size <= size)
    {
        uint32_t result = flashWritePage(
            &flashConfig,
            base_address + written,
            (uint8_t *)&bitstream[written],
            page_size
        );

        if (result != page_size)
        {
            uint64_t elapsed = time_us_64() - start;

            task_context->task_services.send_data(
                &task_context->task_services,
                0,
                (uint8_t *)&elapsed,
                sizeof(elapsed),
                false
            );

            task_context->task_services.send_data(
                &task_context->task_services,
                1,
                (uint8_t *)&written,
                sizeof(written),
                false
            );

            task_context->task_services.send_return(
                &task_context->task_services,
                1,
                0,
                false
            );
            return;
        }

        written += page_size;
    }

    uint64_t elapsed = time_us_64() - start;

    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        (uint8_t *)&elapsed,
        sizeof(elapsed),
        false
    );

    task_context->task_services.send_data(
        &task_context->task_services,
        1,
        (uint8_t *)&written,
        sizeof(written),
        false
    );

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false
    );
}
/* ============================================================
 * SKELETON / MODEL ID
 * ============================================================ */

#define ADDR_MODEL_ID 0
#define BYTES_MODEL_ID 16

void read_skeleton_id_core(
    uint8_t *skeleton_id)
{
    if (flashConfig.spiConfiguration->spiInstance == NULL)
    {
        init_hardware();
    }

    Fpga *fpga = Config_getFpga();

    if (!Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOn(fpga);

        sleep_ms(100);
    }

    FpgaMiddleware *fpga_middleware =
        Config_getFpgaMiddleware();

    FpgaMiddleware_init(fpga_middleware);

    FpgaMiddleware_enableUserLogic(
        fpga_middleware);

    FpgaMiddleware_read(
        fpga_middleware,
        skeleton_id,
        ADDR_MODEL_ID,
        BYTES_MODEL_ID);

    FpgaMiddleware_disableUserLogic(
        fpga_middleware);

    FpgaMiddleware_deinit(
        fpga_middleware);
}

/*
 * Normal remote task.
 *
 * No local timing is performed here.
 */
void p_read_skeleton_id(TaskContext *task_context)
{
    uint8_t skeleton_id[BYTES_MODEL_ID] = {0};

    read_skeleton_id_core(
        skeleton_id);

    /*
     * data_id = 0 -> skeleton ID
     */
    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        skeleton_id,
        BYTES_MODEL_ID,
        false);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}

/*
 * Direct benchmark.
 *
 * The complete read_skeleton_id_core() execution is timed.
 * Protocol communication happens after the timer has stopped.
 */
void benchmark_read_skeleton_id(TaskContext *task_context)
{
    uint8_t skeleton_id[BYTES_MODEL_ID] = {0};

    uint64_t start = time_us_64();

    read_skeleton_id_core(
        skeleton_id);

    uint64_t elapsed =
        time_us_64() - start;

    /*
     * data_id = 0 -> execution time
     */
    task_context->task_services.send_data(
        &task_context->task_services,
        0,
        (uint8_t *)&elapsed,
        sizeof(elapsed),
        false);

    /*
     * data_id = 1 -> skeleton ID
     */
    task_context->task_services.send_data(
        &task_context->task_services,
        1,
        skeleton_id,
        BYTES_MODEL_ID,
        false);

    task_context->task_services.send_return(
        &task_context->task_services,
        0,
        0,
        false);
}