#include "experiment/Fpga.h"
#include <stdint.h>

typedef struct FpgaPins
{
    uint8_t reset;
    uint8_t voltage_regulator_enable;
    uint8_t mos_fets_enable;
    uint8_t busy;
} FpgaPins;

struct Fpga
{
    const FpgaPins *pins;
    uint8_t is_powered;
};
