#include "transport.h"

#include <stdio.h>
#include "pico/stdlib.h"
#include "ringbuffer.h"

typedef struct
{
    RingBuffer *rb;

} UsbTransportImpl;

/**
 * Send one byte via Pico stdio USB
 */
static void usb_send_byte(Transport *self, uint8_t b)
{
    (void)self;

    putchar_raw(b);
    fflush(stdout);
}

/**
 * Non-blocking receive
 *
 * Returns:
 *   byte if available
 *   0 if no byte available
 *
 * NOTE:
 * This interface cannot distinguish
 * "no byte" from byte value 0.
 */
static uint8_t usb_recv_byte(Transport *self)
{
    UsbTransportImpl *impl =
        (UsbTransportImpl *)self->impl;

    uint8_t b = 0;

    ringbuffer_pop(impl->rb, &b);

    return b;
}

/**
 * Poll Pico stdio USB and fill RX ringbuffer
 */
static void usb_poll_rx(Transport *self)
{
    UsbTransportImpl *impl =
        (UsbTransportImpl *)self->impl;

    uint32_t rb_free_size = ringbuffer_free_space(impl->rb);

    while (rb_free_size > 0)
    {
        int c = stdio_getchar_timeout_us(0);

        if (c == PICO_ERROR_TIMEOUT)
            break;

        uint8_t b = (uint8_t)c;

        ringbuffer_push(impl->rb, &b);
        rb_free_size--;
    }
}

static void usb_destroy(Transport *self)
{
    (void)self;
}

/**
 * Init USB transport using pico_stdio_usb
 */
void transport_init(Transport *transport, TransportConfig cfg)
{
    UsbTransportImpl *impl =
        (UsbTransportImpl *)transport->impl;

    impl->rb = cfg.incoming_rb;

    transport->send_byte = usb_send_byte;
    transport->recv_byte = usb_recv_byte;
    transport->destroy = usb_destroy;

    transport->incoming_rb = cfg.incoming_rb;

    stdio_init_all();
}

/**
 * Public service function
 */
void transport_poll(Transport *transport)
{
    usb_poll_rx(transport);
}

uint64_t transport_get_current_time()
{
    return to_ms_since_boot(get_absolute_time()) / 1000;
}