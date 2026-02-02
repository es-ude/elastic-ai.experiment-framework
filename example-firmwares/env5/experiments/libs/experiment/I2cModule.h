#ifndef I2C_H
#define I2C_H

#include <stdbool.h>

typedef struct I2cModule I2cModule;

typedef struct I2cFns {
  bool (*isInitialized)(I2cModule *self);
  void (*init)(I2cModule *self);
} I2cFns;

typedef struct I2cModule {
  const I2cFns *fns;
} I2cModule;

static bool I2cModule_isInitialized(I2cModule *self) {
  return self->fns->isInitialized(self);
}

static void I2cModule_init(I2cModule *self) {
  self->fns->init(self);
}

#endif //I2C_H
