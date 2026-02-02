#include "experiment/I2cModule.h"
#include "experiment/I2cPico.h"

#include <stdlib.h>

#include "I2c.h"

static I2cPico *cast(I2cModule *self)
{
  return (I2cPico *)self;
}

static void init(I2cModule *self)
{
  I2cPico *this = cast(self);
  i2cInit(this->handle);
  this->initialized = true;
}

static bool isInitialized(I2cModule *self)
{
  I2cPico *this = cast(self);
  return this->initialized;
}

I2cPico createI2cPico(i2cConfiguration_t *config)
{
  static const I2cFns fns = {
      .isInitialized = isInitialized,
      .init = init,
  };
  return (I2cPico){
      .handle = config,
      .module = {
          .fns = &fns,
      }};
}