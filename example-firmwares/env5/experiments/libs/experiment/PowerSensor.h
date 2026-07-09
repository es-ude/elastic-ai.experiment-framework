#ifndef POWERSENSOR_H
#define POWERSENSOR_H

#define PAC193X_CHANNEL_FPGA_IO PAC193X_CHANNEL01
#define PAC193X_CHANNEL_FPGA_1V8 PAC193X_CHANNEL02
#define PAC193X_CHANNEL_FPGA_1V PAC193X_CHANNEL03
#define PAC193X_CHANNEL_FPGA_SRAM PAC193X_CHANNEL04

enum {
  POWER_SENSOR_SAMPLING_RATE_1024,
};


typedef struct PowerSensor PowerSensor;

typedef struct PowerSensorFns {
  void (*setSamplingRate)(PowerSensor*, int);
  void (*init)(PowerSensor*);
} PowerSensorFns;

struct PowerSensor {
  const PowerSensorFns *fns;
};

static void PowerSensor_setSamplingRate(PowerSensor *self, int samplingRate) {
  self->fns->setSamplingRate(self, samplingRate);
}

static void PowerSensor_init(PowerSensor *self) {
  self->fns->init(self);
}

#endif //POWERSENSOR_H
