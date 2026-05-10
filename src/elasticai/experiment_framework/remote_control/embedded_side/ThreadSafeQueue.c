#include <stdlib.h>
#include <string.h>

#include "ThreadSafeQueue.h"

struct ThreadSafeQueue
{
    void *buffer;

    size_t elem_size;
    size_t capacity;

    int head;
    int tail;
    int count;

    pthread_mutex_t mutex;
    pthread_cond_t cond;
};

bool queue_push(ThreadSafeQueue *self, const void *item)
{
    pthread_mutex_lock(&self->mutex);

    if (self->count == self->capacity)
    {
        pthread_mutex_unlock(&self->mutex);
        return false;
    }

    void *target =
        (char *)self->buffer +
        (self->tail * self->elem_size);

    memcpy(target, item, self->elem_size);

    self->tail =
        (self->tail + 1) % self->capacity;

    self->count++;

    pthread_cond_signal(&self->cond);

    pthread_mutex_unlock(&self->mutex);

    return true;
}

bool queue_pop(ThreadSafeQueue *self, void *out)
{
    pthread_mutex_lock(&self->mutex);

    while (self->count == 0)
    {
        pthread_cond_wait(&self->cond,
                          &self->mutex);
    }

    void *source =
        (char *)self->buffer +
        (self->head * self->elem_size);

    memcpy(out, source, self->elem_size);

    self->head =
        (self->head + 1) % self->capacity;

    self->count--;

    pthread_mutex_unlock(&self->mutex);

    return true;
}

void queue_destroy(ThreadSafeQueue *self)
{
    free(self->buffer);

    pthread_mutex_destroy(&self->mutex);
    pthread_cond_destroy(&self->cond);
}

ThreadSafeQueue *queue_create(size_t capacity, size_t elem_size)
{
    ThreadSafeQueue *queue = malloc(sizeof(ThreadSafeQueue));
    queue->buffer = malloc(capacity * elem_size);

    queue->capacity = capacity;
    queue->elem_size = elem_size;

    queue->head = 0;
    queue->tail = 0;
    queue->count = 0;

    pthread_mutex_init(&queue->mutex, NULL);
    pthread_cond_init(&queue->cond, NULL);
    return queue;
}