cmake_minimum_required(VERSION 3.16)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)


enable_testing()

# =========================
# OPTIONS
# =========================

option(ENABLE_ASAN "Enable AddressSanitizer" OFF)

# =========================
# INIT
# =========================

if(NOT ELASTIC_AI_TARGET STREQUAL "HOST" AND NOT ELASTIC_AI_TARGET STREQUAL "ENV5_2")
    message(FATAL_ERROR "Unknown PLATFORM: ${ELASTIC_AI_TARGET}")
endif()

message(STATUS "Building for ${ELASTIC_AI_TARGET}")

include(${CMAKE_CURRENT_LIST_DIR}/cmake/load_third_party_deps.cmake)

if(ELASTIC_AI_TARGET STREQUAL "HOST")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -std=gnu99")
endif()

add_runtime_enV5("v7.1.0")
project(embedded_remote_control C CXX ASM)
eai_runtime_init()

add_subdirectory(src)

# =========================
# TESTS
# =========================

if(ELASTIC_AI_TARGET STREQUAL "HOST")

    add_subdirectory(
        ${CMAKE_SOURCE_DIR}/tests/unit
    )

endif()