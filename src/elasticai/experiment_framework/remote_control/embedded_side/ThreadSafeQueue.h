#ifndef TSQ_H
#define TSQ_H

#include <stddef.h>
#include <stdbool.h>
#include <pthread.h>

typedef struct ThreadSafeQueue ThreadSafeQueue;

bool queue_push(ThreadSafeQueue *self, const void *item);
bool queue_pop(ThreadSafeQueue *self, void *out);
void queue_destroy(ThreadSafeQueue *self);

ThreadSafeQueue *queue_create(size_t capacity, size_t elem_size);

#endif