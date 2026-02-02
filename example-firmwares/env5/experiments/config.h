#ifndef CONFIG_H
#define CONFIG_H

#include "experiment/I2cModule.h"
#include "experiment/Middleware.h"
#include "experiment/Fpga.h"

Fpga *Config_getFpga(void);

I2cModule *Config_getI2c_2(void);

void init_hardware(void);
FpgaMiddleware *Config_getFpgaMiddleware(void);
Spi *Config_getFpgaSpi(void);

#endif // CONFIG_H
