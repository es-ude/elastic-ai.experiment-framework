#ifndef SPIPICO_H
#define SPIPICO_H

#include "Spi.h"

typedef struct spi_inst spi_inst_t;

/*
 * supports only MSB_FIRST for order!
 */
Spi *PicoSpi_create(struct spi_inst *);
#endif // SPIPICO_H
