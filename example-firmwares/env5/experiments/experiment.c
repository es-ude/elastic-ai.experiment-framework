#include <sys/unistd.h>

#include "EnV5HwController.h"
#include "Flash.h"
#include "UsbProtocolBase.h"
#include "UsbProtocolCustomCommands.h"

#include "CException.h"
#include "pico/time.h"
#include "I2c.h"
#include "middleware.h"
#include "Pac193xTypedefs.h"
#include "experiment/Middleware.h"
#include "config.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "EnV5HwConfiguration.h"

#define MAX_RETRIES 5

static void startCompute(void)
{
    uint8_t cmd[1] = {0x01};
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_write(fpga, cmd, 16, 1);
}
static void stopCompute(void)
{
    uint8_t cmd[1] = {0x00};
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_write(fpga, cmd, 16, 1);
}

static uint32_t max(uint32_t a, uint32_t b)
{
    return (a > b) ? a : b;
}

static void predict(const uint8_t *input_data, size_t input_length, uint8_t *output_data, size_t output_length)
{
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_init(fpga);
    FpgaMiddleware_enableUserLogic(fpga);
    FpgaMiddleware_write(fpga, input_data, 18, input_length);
    startCompute();
    while (FpgaMiddleware_fpgaIsBusy(fpga))
    {
    }
    stopCompute();
    FpgaMiddleware_read(fpga, output_data, 18, output_length);
    FpgaMiddleware_disableUserLogic(fpga);
    FpgaMiddleware_deinit(fpga);
}

static void receiveInput(uint8_t *buffer, size_t bufferLength, size_t chunk_size)
{

    uint8_t nackCounter = 0;
    uint8_t *current_chunk = buffer;
    size_t remaining_byte;
    while (remaining_byte > 0)
    {
        if (nackCounter >= MAX_RETRIES)
        {
            Throw(5);
        }

        usbProtocolMessage_t message;
        if (!usbProtocolReadMessage(&message))
        {
            nackCounter++;
            continue;
        }
        else
        {
            memcpy(current_chunk, message.payload, message.payloadLength);

            current_chunk += message.payloadLength;
            remaining_byte -= message.payloadLength;
            nackCounter = 0;

            free(message.payload);
        }
    }
}

static void sendOutput(uint8_t *buffer, uint8_t command, size_t bufferLength, size_t chunk_size)
{
    int remainingBytes = bufferLength;
    uint8_t nackCounter = 0;
    usbProtocolMessage_t message;
    message.command = command;
    uint8_t *current_chunk = buffer;
    while (remainingBytes > 0)
    {
        if (nackCounter > MAX_RETRIES)
        {
            Throw(5);
        }
        if (remainingBytes >= chunk_size)
        {
            message.payloadLength = chunk_size;
        }
        else
        {
            message.payloadLength = remainingBytes;
        }
        message.payload = current_chunk;
        bool success = usbProtocolSendMessage(&message);
        if (!success)
        {
            nackCounter++;
        }
        else
        {
            current_chunk += message.payloadLength;
            remainingBytes -= message.payloadLength;
            nackCounter = 0;
        }
    }
}

static uint32_t convertByteArrayToUint32(const uint8_t in[4])
{
    return in[0] << 24 | in[1] << 16 | in[2] << 8 | in[3];
}

static uint16_t convertByteArrayToUint16(const uint8_t in[2])
{
    return in[0] << 8 | in[1];
}

void get_id(const uint8_t *,
            size_t)
{
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_init(fpga);
    FpgaMiddleware_enableUserLogic(fpga);
    uint8_t id[16] = {0};
    FpgaMiddleware_read(fpga, id, 0, 16);
    FpgaMiddleware_disableUserLogic(fpga);
    FpgaMiddleware_deinit(fpga);
    usbProtocolMessage_t msg = {.command = 242,
                                .payloadLength = sizeof(id),
                                .payload = id};
    usbProtocolSendMessage(&msg);
}

enum COMMANDS
{
    READ_WRITE_FPGA_SPI = 250
};

/**
 * @brief Directly transfer data
 *
 * @param data
 * @param length
 */
void read_write_fpga_spi(const uint8_t *data, size_t length)
{
    Spi *spi = Config_getFpgaSpi();
    Spi_init(spi);
    Spi_select(spi, FPGA_SPI_CS);
    Fpga *fpga = Config_getFpga();
    while (Fpga_isBusy(fpga))
        ;
    uint8_t result[length];
    Spi_read_write(spi, data, result, length);
    Spi_deselect(spi, FPGA_SPI_CS);
    Spi_deinit(spi);
    usbProtocolMessage_t msg = {
        .command = READ_WRITE_FPGA_SPI,
        .payload = result,
        .payloadLength = length};
    usbProtocolSendMessage(&msg);
};

_Noreturn void runExperiment(void)
{
    while (true)
    {
        CEXCEPTION_T exception;
        Try
        {
            usbProtocolReceiveBuffer received = usbProtocolWaitForCommand();
            usbProtocolHandleCommand(received);
        }
        Catch(exception)
        {
            env5HwControllerLedsAllOn();
            sleep_ms(1000);
            env5HwControllerLedsAllOff();
            sleep_ms(1000);
            env5HwControllerLedsAllOn();
            sleep_ms(1000);
            env5HwControllerLedsAllOff();
        }
    }
}

typedef struct ChunkWriter ChunkWriter;
struct ChunkWriter
{
    uint8_t *start_position;
    uint8_t *current_position;
    void (*write)(ChunkWriter *, const uint8_t *, int);
};

void writeChunk(ChunkWriter *self, const uint8_t *src, int size)
{
    memcpy(self->current_position, src, size);
    self->current_position += size;
}

void receiveChunks(size_t total_size, ChunkWriter *writer)
{
    usbProtocolMessage_t msg;
    int32_t remainder = total_size;
    while (remainder > 0)
    {
        usbProtocolReadMessage(&msg);
        remainder -= msg.payloadLength;
        writer->write(writer, msg.payload, msg.payloadLength);
        free(msg.payload);
    }
}

void fake_inference(const uint8_t *data, size_t length)
{
    uint32_t input_length = convertByteArrayToUint32(data);
    uint32_t output_length = convertByteArrayToUint32(data + sizeof(uint32_t));
    uint32_t max_length = max(input_length, output_length);
    uint8_t buffer[max_length];
    memset(buffer, 0, max_length);
    ChunkWriter writer = {.current_position = buffer, .start_position = buffer, .write = writeChunk};
    receiveChunks(input_length, &writer);
    sendOutput(buffer, 244, output_length, 256);
}

void inference(const uint8_t *data, size_t length)
{
    uint32_t input_length = convertByteArrayToUint32(data);
    uint32_t output_length = convertByteArrayToUint32(data + sizeof(uint32_t));
    uint32_t max_length = max(input_length, output_length);
    uint8_t buffer[max_length];
    memset(buffer, 0, max_length);
    ChunkWriter writer = {.current_position = buffer, .start_position = buffer, .write = writeChunk};
    receiveChunks(input_length, &writer);
    predict(buffer, input_length, buffer, output_length);
    sendOutput(buffer, 244, output_length, 1 << 9);
}

typedef struct Command
{
    void (*fn)(const uint8_t *, size_t);
    uint8_t id;
} Command;

int main(void)
{
    init_hardware();
    Command commands[] = {
        {.fn = get_id, .id = 242},
        {.fn = inference, .id = 243},
        {.fn = fake_inference, .id = 244},
        {.fn = read_write_fpga_spi, .id = READ_WRITE_FPGA_SPI},
    };
    for (int i = 0; i < sizeof(commands) / sizeof(commands[0]); i++)
    {
        usbProtocolRegisterCommand(commands[i].id, commands[i].fn);
    }

    runExperiment();
}
