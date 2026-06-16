#pragma once

#ifdef ENABLE_LOGGING

#include <stdio.h>

#define LOG(fmt, ...)               \
    do                              \
    {                               \
        printf(fmt, ##__VA_ARGS__); \
        fflush(stdout);             \
    } while (0)

#else

#define LOG(fmt, ...) \
    do                \
    {                 \
    } while (0)

#endif