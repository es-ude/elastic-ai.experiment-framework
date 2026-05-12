#include <pthread.h>
#include <stdlib.h>

#include "connection_manager.h"
#include "task_manager.h"
#include "sender.h"
#include "receiver.h"

int main(int argc, char const *argv[])
{
    ThreadArgs args;

    if (argc >= 3)
    {
        args.host = argv[1];

        args.port = atoi(argv[2]);
    }
    else
    {
        args.host = "127.0.0.1";

        args.port = 8080;
    }

    init_sending_queue();

    pthread_t receiving_t, sending_t, tasks_t;

    pthread_create(&receiving_t, NULL, receiving_thread, &args);
    pthread_create(&sending_t, NULL, sending_thread, NULL);
    pthread_create(&tasks_t, NULL, tasks_thread, NULL);

    pthread_join(receiving_t, NULL); // Wait for receiving thread to return. In normal cases it shouldnt

    return 0;
}
