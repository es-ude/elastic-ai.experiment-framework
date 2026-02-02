cmake_minimum_required(VERSION 3.21...3.24)
include(${CMAKE_SOURCE_DIR}/cmake/load_third_party_deps.cmake)
set(ELASTIC_AI_TARGET ENV5_REV2)

add_runtime_enV5("v5.6.2")

project(enV5-application C CXX ASM)

eai_runtime_init()

add_unity()
add_ctest()

add_subdirectory(experiments)

if (BUILDING_FOR_ELASTIC_NODE AND NOT TARGET tinyusb_device)
    message(WARNING "not building project, because tinyusb not initialized")
endif ()
