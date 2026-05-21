#pragma once

#include <stdint.h>
#include <stdbool.h>

typedef struct
{
    uint8_t *buffer;

    uint16_t head;
    uint16_t tail;

    uint16_t capacity;
    uint16_t elem_size;

} RingBuffer;

void ringbuffer_init(RingBuffer *rb,
                     void *buffer,
                     uint16_t capacity,
                     uint16_t elem_size);
bool ringbuffer_push(RingBuffer *rb, const void *item);
bool ringbuffer_pop(RingBuffer *rb, void *out);