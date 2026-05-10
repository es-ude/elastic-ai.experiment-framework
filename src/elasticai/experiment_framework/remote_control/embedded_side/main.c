#include <pthread.h>

#include "connection_manager.h"
#include "task_manager.h"
#include "sender.h"
#include "receiver.h"

int main(int argc, char const *argv[])
{
    init_sending_queue();

    pthread_t receiving_t, sending_t, tasks_t;

    pthread_create(&receiving_t, NULL, receiving_thread, NULL);
    pthread_create(&sending_t, NULL, sending_thread, NULL);
    pthread_create(&tasks_t, NULL, tasks_thread, NULL);

    pthread_join(receiving_t, NULL); // Wait for receiving thread to return. In normal cases it shouldnt

    return 0;
}
