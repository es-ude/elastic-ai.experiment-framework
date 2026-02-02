#include "hardware/gpio.h"
#include "pico/time.h"
#include "experiment/PicoFpga.h"

static void make_output_pin(uint8_t pin_number, uint8_t initial_mode);
static void make_input_pin(uint8_t pin_number);
static void enable_mosfets(const Fpga *self);
static void disable_mosfets(const Fpga *self);
static void enable_voltage_regulator(const Fpga *self);
static void disable_voltage_regulator(const Fpga *self);

void Fpga_init(Fpga *self)
{
    make_output_pin(self->pins->reset, 1);

    make_output_pin(self->pins->voltage_regulator_enable, 0);

    make_output_pin(self->pins->mos_fets_enable, 0);
    make_input_pin(self->pins->busy);
    self->is_powered = 0;
}

void Fpga_powerOn(Fpga *self)
{
    enable_voltage_regulator(self);
    sleep_ms(10); // wait until fpga is powered up
    enable_mosfets(self);
    self->is_powered = 1;
}

void Fpga_powerOff(Fpga *self)
{
    disable_voltage_regulator(self);
    disable_mosfets(self);
    sleep_ms(1); // not sure this is necessary, original code did this
    self->is_powered = 0;
}

bool Fpga_isPoweredOn(const Fpga *self)
{
    return self->is_powered == 1;
}

bool Fpga_isBusy(const Fpga *self)
{
    return self->pins->busy == 1;
}

void make_output_pin(uint8_t pin_number, uint8_t initial_mode)
{
    gpio_init(pin_number);
    gpio_set_dir(pin_number, GPIO_OUT);
    gpio_put(pin_number, initial_mode);
}

void make_input_pin(uint8_t pin_number)
{
    gpio_init(pin_number);
    gpio_set_dir(pin_number, GPIO_IN);
}

void enable_mosfets(const Fpga *self)
{
    gpio_put(self->pins->mos_fets_enable, 0);
}

void disable_mosfets(const Fpga *self)
{
    gpio_put(self->pins->mos_fets_enable, 1);
}

void enable_voltage_regulator(const Fpga *self)
{
    gpio_put(self->pins->voltage_regulator_enable, 1);
}

void disable_voltage_regulator(const Fpga *self)
{
    gpio_put(self->pins->voltage_regulator_enable, 0);
}
