#ifndef CONFIG_H
#define CONFIG_H

#include "hardware_functions/Middleware.h"
#include "hardware_functions/Fpga.h"
#include "eai/flash/Flash.h"

extern spiConfiguration_t flashSpi;
extern flashConfiguration_t flashConfig;

Fpga *Config_getFpga(void);

void init_hardware(void);
FpgaMiddleware *Config_getFpgaMiddleware(void);
Spi *Config_getFpgaSpi(void);

#endif // CONFIG_H
