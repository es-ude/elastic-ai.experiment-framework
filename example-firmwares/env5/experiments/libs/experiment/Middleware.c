#include "Middleware.h"

#include <stddef.h>

#include "experiment/Spi.h"
#include "hardware/gpio.h"

enum FpgaPowerStatus
{
  FPGA_OFF,
  FPGA_IDLE,
  FPGA_BUSY,
};

enum FpgaMiddlewareState
{
  FPGA_MIDDLEWARE_USERLOGIC_ENABLED,
  FPGA_MIDDLEWARE_INITIALIZED,
  FPGA_MIDDLEWARE_UNINITIALIZED
};

static const FpgaMiddlewareAddresses default_addresses = {
    .leds = 0x0003,
    .user_logic_reset = 0x0004,
    .multi_boot = 0x0005,
    .user_logic_offset = 0x0100,
    .fpga_busy_pin = 15};

typedef struct FpgaMiddleware
{
  Spi *spi;
  SpiConfig *spiConfig;
  uint8_t powerStatus;
  uint8_t state;
  uint8_t slaveHandle;
  const FpgaMiddlewareAddresses *addresses;
} FpgaMiddleware;

static void write(FpgaMiddleware *self, const uint8_t *data, uint16_t startAddress, uint16_t length)
{
  Spi_select(self->spi, self->slaveHandle);
  uint8_t cmd[3] = {0x80, startAddress >> 8, startAddress};
  Spi_write(self->spi, cmd, sizeof(cmd));
  Spi_write(self->spi, data, length);
  Spi_deselect(self->spi, self->slaveHandle);
}

static void read(FpgaMiddleware *self, uint8_t *data, uint16_t startAddress, uint16_t length)
{
  Spi_select(self->spi, self->slaveHandle);
  uint8_t cmd[3] = {0x40, (startAddress >> 8) & 0xFF, startAddress & 0xFF};
  Spi_write(self->spi, cmd, sizeof(cmd));
  Spi_read(self->spi, data, length);
  Spi_deselect(self->spi, self->slaveHandle);
}

FpgaMiddleware *FpgaMiddleware_new(Spi *spi, uint8_t slaveHandle)
{
  static FpgaMiddleware middleware = {
      .spiConfig = NULL,
      .powerStatus = FPGA_OFF,
      .state = FPGA_MIDDLEWARE_UNINITIALIZED,
      .addresses = &default_addresses};
  middleware.slaveHandle = slaveHandle;
  middleware.spi = spi;
  Spi_setupSlave(spi, slaveHandle);
  return &middleware;
}

static void setBusyPinToInput(const FpgaMiddleware *self)
{
  gpio_set_dir(self->addresses->fpga_busy_pin, false);
}

void FpgaMiddleware_init(FpgaMiddleware *self)
{
  Spi_init(self->spi);
  setBusyPinToInput(self);
  Spi_setupSlave(self->spi, self->slaveHandle);
  self->state = FPGA_MIDDLEWARE_INITIALIZED;
}

void FpgaMiddleware_deinit(FpgaMiddleware *self)
{
  if (self->state == FPGA_MIDDLEWARE_USERLOGIC_ENABLED)
  {
    FpgaMiddleware_disableUserLogic(self);
  }
  Spi_deinit(self->spi);
  self->state = FPGA_MIDDLEWARE_UNINITIALIZED;
}

void FpgaMiddleware_enableUserLogic(FpgaMiddleware *self)
{
  if (self->state == FPGA_MIDDLEWARE_UNINITIALIZED)
  {
    FpgaMiddleware_init(self);
  }
  if (self->state == FPGA_MIDDLEWARE_INITIALIZED)
  {
    uint8_t enable = 0x00;
    write(self, &enable, self->addresses->user_logic_reset, sizeof(enable));
    self->state = FPGA_MIDDLEWARE_USERLOGIC_ENABLED;
  }
}

void FpgaMiddleware_disableUserLogic(FpgaMiddleware *self)
{
  if (self->state == FPGA_MIDDLEWARE_UNINITIALIZED)
  {
    FpgaMiddleware_init(self);
  }
  if (self->state == FPGA_MIDDLEWARE_USERLOGIC_ENABLED)
  {
    uint8_t disable = 0x01;
    write(self, &disable, self->addresses->user_logic_reset, sizeof(disable));
    self->state = FPGA_MIDDLEWARE_INITIALIZED;
  }
}

void FpgaMiddleware_read(FpgaMiddleware *self, uint8_t *data, uint16_t startAddress, uint16_t length)
{
  read(self, data, startAddress + self->addresses->user_logic_offset, length);
}

void FpgaMiddleware_write(FpgaMiddleware *self, const uint8_t *data, uint16_t startAddress, uint16_t length)
{
  write(self, data, startAddress + self->addresses->user_logic_offset, length);
}

void FpgaMiddleware_setAddresses(FpgaMiddleware *self, const FpgaMiddlewareAddresses *addresses);

bool FpgaMiddleware_fpgaIsBusy(FpgaMiddleware *self)
{
  return gpio_get(self->addresses->fpga_busy_pin) == 1;
}

bool FpgaMiddleware_isIdle(FpgaMiddleware *self)
{
  return gpio_get(self->addresses->fpga_busy_pin) == 0;
}