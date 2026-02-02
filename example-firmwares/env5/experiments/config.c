#include "config.h"
#include "EnV5HwConfiguration.h"

#include "pico/stdio_usb.h"
#include "pico/time.h"
#include "hardware/spi.h"
#include "EnV5HwController.h"
#include "Flash.h"
#include "EnV5HwConfiguration.h"
#include "UsbProtocolBase.h"

#include "experiment/Middleware.h"
#include "experiment/SpiPico.h"

#include "experiment/I2cPico.h"
#include "experiment/I2cModule.h"

#include "experiment/PicoFpga.h"

Fpga *Config_getFpga(void)
{
  static const FpgaPins env5_fpga_pins = {
      .busy = 15,
      .mos_fets_enable = 21,
      .voltage_regulator_enable = 23,
      .reset = 12};
  static Fpga fpga = {
      .pins = &env5_fpga_pins,
      .is_powered = 0};
  return &fpga;
}

usbProtocolErrorCodes_t readByteForProtocol(uint8_t *readBuffer, size_t numOfBytes)
{
  for (size_t index = 0; index < numOfBytes; index++)
  {
    readBuffer[index] = stdio_getchar();
  }
  return USB_PROTOCOL_OKAY;
}

usbProtocolErrorCodes_t sendBytesForProtocol(uint8_t *sendBuffer, size_t numOfBytes)
{
  for (size_t index = 0; index < numOfBytes; index++)
  {
    stdio_putchar_raw(sendBuffer[index]);
  }
  return USB_PROTOCOL_OKAY;
}

Spi *Config_getFpgaSpi(void)
{
  static Spi *fpgaSpi = NULL;
  static SpiConfig fpgaSpiConfig = {
      .baudrate = 10000 * 1000,
      .misoPin = FPGA_SPI_MISO,
      .mosiPin = FPGA_SPI_MOSI,
      .sckPin = FPGA_SPI_CLOCK,
      .data_bits = 8,
      .phase = EAI_SPI_CPHA_1,
      .order = EAI_SPI_MSB_FIRST,
      .polarity = EAI_SPI_CPOL_0};
  if (fpgaSpi == NULL)
  {
    fpgaSpi = PicoSpi_create(FPGA_SPI_MODULE);
    Spi_setConfig(fpgaSpi, &fpgaSpiConfig);
  }
  return fpgaSpi;
}

FpgaMiddleware *Config_getFpgaMiddleware(void)
{
  static FpgaMiddleware *fpga = NULL;

  if (fpga == NULL)
  {
    fpga = FpgaMiddleware_new(Config_getFpgaSpi(), FPGA_SPI_CS);
  }
  return fpga;
}

void init_hardware(void)
{
  static spiConfiguration_t flashSpi = {
      .sckPin = FLASH_SPI_CLOCK,
      .misoPin = FLASH_SPI_MISO,
      .mosiPin = FLASH_SPI_MOSI,
      .csPin = FLASH_SPI_CS,
      .baudrate = FLASH_SPI_BAUDRATE,
  };
  flashSpi.spiInstance = FLASH_SPI_MODULE;

  static flashConfiguration_t flashConfig = {
      .spiConfiguration = &flashSpi,
  };

  env5HwControllerInit();

  stdio_usb_init();
  while (!stdio_usb_connected())
  {
    // wait for serial connection
  }
  sleep_ms(20);
  Fpga_init(Config_getFpga());
  flashInit(&flashConfig);
  usbProtocolInit(readByteForProtocol, sendBytesForProtocol, &flashConfig);
}