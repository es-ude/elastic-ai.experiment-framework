#ifndef FGPA_H
#define FPGA_H

#include <stdbool.h>

typedef struct Fpga Fpga;

void Fpga_powerOn(Fpga *self);
void Fpga_powerOff(Fpga *self);
void Fpga_init(Fpga *self);
bool Fpga_isBusy(const Fpga *self);
bool Fpga_isPoweredOn(const Fpga *self);

#endif