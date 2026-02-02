#ifndef MIDDLEWARE_H
#define MIDDLEWARE_H
#include <stdbool.h>
/**
 * Provides low level routines to interact with an
 * FPGA that is hosting the elasticai middleware.
 * You need to set the spi interface and slave handle
 * to define the slave select line that should be used.
 * The default implementation of the fpga middleware as hosted
 * on the FPGA is stateful and the state needs to be managed
 * by the mcu. That means in most cases you'll want to
 * `init` and `deinit` the middleware. Additionally,
 * prior to interacting with the user logic (i.e., hw function or skeleton),
 * you have ensure the user logic is enabled.
 *
 *
 *
 * IMPORTANT::: While, this software module will keep track of the fpga power
 * status and ensure that the fpga is turned on before you try interacting
 * with it. But this will not work, in case you're using multiple "instances"
 * of FpgaMiddleware in parallel. Then each of them will keep their own state.
 * So clients are responsible for keeping these states consistent.
 *
 */

#include "experiment/Spi.h"

typedef struct FpgaMiddleware FpgaMiddleware;

typedef struct FpgaMiddlewareAddresses
{
    uint16_t leds;
    uint16_t user_logic_offset;
    uint16_t multi_boot;
    uint16_t user_logic_reset;
    uint8_t fpga_busy_pin;
} FpgaMiddlewareAddresses;

/*Create a new middleware instance with default addresses*/
FpgaMiddleware *FpgaMiddleware_new(Spi *spi, uint8_t slaveHandle);

/**
 * Use this to configure the user logic offset and other
 * details in case you want to use your own flavour of
 * the middleware.
 * */
void FpgaMiddleware_setAddresses(FpgaMiddleware *self, const FpgaMiddlewareAddresses *addresses);

bool FpgaMiddleware_fpgaIsBusy(FpgaMiddleware *middleware);
void FpgaMiddleware_init(FpgaMiddleware *self);
void FpgaMiddleware_deinit(FpgaMiddleware *self);
void FpgaMiddleware_enableUserLogic(FpgaMiddleware *self);
void FpgaMiddleware_disableUserLogic(FpgaMiddleware *self);
void FpgaMiddleware_read(FpgaMiddleware *self, uint8_t *data, uint16_t startAddress, uint16_t length);
void FpgaMiddleware_write(FpgaMiddleware *self, const uint8_t *data, uint16_t startAddress, uint16_t length);

#endif // MIDDLEWARE_H
