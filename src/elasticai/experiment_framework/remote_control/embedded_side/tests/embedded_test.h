#include <stdint.h>

typedef struct
{
    uint8_t fnc_id;
    char *message;
} cli_params;

void *client_thread(void *arg);