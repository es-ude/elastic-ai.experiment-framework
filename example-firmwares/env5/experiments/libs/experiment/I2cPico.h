#ifndef PRIVATEI2C_H
#define PRIVATEI2C_H

#include "I2cTypedefs.h"

typedef struct I2cPico {
  I2cModule module;
  i2cConfiguration_t *handle;
  bool initialized;
} I2cPico;

I2cPico createI2cPico(i2cConfiguration_t *handle);

#endif //PRIVATEI2C_H
