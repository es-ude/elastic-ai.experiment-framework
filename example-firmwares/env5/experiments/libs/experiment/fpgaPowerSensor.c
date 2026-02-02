#include "hardware/i2c.h"

#include "EnV5HwConfiguration.h"
#include "Pac193x.h"
#include "Pac193xTypedefs.h"
#include "experiment/fpgaPowerSensor.h"
#include "PowerSensor.h"
#include "experiment/I2cModule.h"

#define PAC193X_CHANNEL_FPGA_IO PAC193X_CHANNEL01
#define PAC193X_CHANNEL_FPGA_1V8 PAC193X_CHANNEL02
#define PAC193X_CHANNEL_FPGA_1V PAC193X_CHANNEL03
#define PAC193X_CHANNEL_FPGA_SRAM PAC193X_CHANNEL04

typedef struct FPGASensor
{
  PowerSensor parent;
  pac193xSensorConfiguration_t *handle;
  I2cModule *i2c;
} FPGASensor;

static FPGASensor *cast(PowerSensor *self)
{
  return (FPGASensor *)self;
}

static void setSamplingRate(PowerSensor *self, int sampling_rate)
{
  FPGASensor *this = cast(self);
  switch (sampling_rate)
  {
  case POWER_SENSOR_SAMPLING_RATE_1024:
    pac193xSetSampleRate(*this->handle, PAC193X_1024_SAMPLES_PER_SEC);
  default:
    pac193xSetSampleRate(*this->handle, PAC193X_1024_SAMPLES_PER_SEC);
  }
}

static void init(PowerSensor *self)
{
  FPGASensor *this = cast(self);
  if (!I2cModule_isInitialized(this->i2c))
  {
    I2cModule_init(this->i2c);
  }
  pac193xInit(*this->handle);
}

PowerSensor *getFpgaPowerSensor(I2cModule *i2c)
{
  static pac193xSensorConfiguration_t handle = {

      .i2c_slave_address = PAC_TWO_SLAVE,
      .powerPin = PAC_TWO_POWER_PIN,
      .usedChannels = PAC_TWO_USED_CHANNELS,
      .rSense = PAC_TWO_R_SENSE,
  };
  handle.i2c_host = PAC_TWO_I2C_MODULE;
  static const PowerSensorFns fns = {
      .setSamplingRate = setSamplingRate,
      .init = init,
  };
  static FPGASensor self = {
      .handle = &handle,
      .parent.fns = &fns,
  };
  self.i2c = i2c;
  return (PowerSensor *)&self;
}
