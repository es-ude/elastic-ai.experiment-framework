#include "ringbuffer.h"
#include <string.h>

void ringbuffer_init(RingBuffer *rb,
                     void *buffer,
                     uint16_t capacity,
                     uint16_t elem_size)
{
    rb->buffer = (uint8_t *)buffer;
    rb->capacity = capacity;
    rb->elem_size = elem_size;

    rb->head = 0;
    rb->tail = 0;
}

bool ringbuffer_empty(RingBuffer *rb)
{
    return rb->head == rb->tail;
}

bool ringbuffer_full(RingBuffer *rb)
{
    return ((rb->head + 1) % rb->capacity) == rb->tail;
}

bool ringbuffer_push(RingBuffer *rb, const void *item)
{
    uint16_t next = (rb->head + 1) % rb->capacity;

    if (next == rb->tail)
        return false;
    void *dst =
        rb->buffer +
        (rb->head * rb->elem_size);

    memcpy(dst, item, rb->elem_size);
    rb->head = next;
    return true;
}

bool ringbuffer_pop(RingBuffer *rb, void *out)
{

    if (rb->head == rb->tail)
        return false;

    void *src =
        rb->buffer +
        (rb->tail * rb->elem_size);

    if (out != 0)
    {
        memcpy(out, src, rb->elem_size);
    }

    rb->tail = (rb->tail + 1) % rb->capacity;

    return true;
}

int ringbuffer_size(RingBuffer *rb)
{
    if (rb->head >= rb->tail)
    {
        return rb->head - rb->tail;
    }
    else
    {
        return rb->capacity - (rb->tail - rb->head);
    }
}