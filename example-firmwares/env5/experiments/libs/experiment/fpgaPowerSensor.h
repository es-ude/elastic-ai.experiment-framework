#ifndef FPGAPOWERSENSOR_H
#define FPGAPOWERSENSOR_H
#include "experiment/I2cModule.h"

typedef struct PowerSensor PowerSensor;

PowerSensor *getFpgaPowerSensor(I2cModule *i2c);

#endif