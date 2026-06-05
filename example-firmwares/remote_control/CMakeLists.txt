cmake_minimum_required(VERSION 3.10)
project(embedded_remote_control C)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

enable_testing()

# =========================
# PATHS
# =========================

set(SRC_LIB ${CMAKE_SOURCE_DIR}/src/lib)
set(SRC_APP ${CMAKE_SOURCE_DIR}/src/app)
set(SRC_TRANSPORT ${CMAKE_SOURCE_DIR}/src/transport)
set(SRC_UNIT_TESTS ${CMAKE_SOURCE_DIR}/tests/unit)

# =========================
# CORE LIB
# =========================

add_library(remote_core
    ${SRC_LIB}/embedded_functions.c
    ${SRC_LIB}/frame_builder.c
    ${SRC_LIB}/msg_handler.c
    ${SRC_LIB}/receiver.c
    ${SRC_LIB}/ringbuffer.c
    ${SRC_LIB}/sender.c
    ${SRC_LIB}/task_manager.c
)

target_include_directories(remote_core PUBLIC
    ${SRC_LIB}
    ${SRC_TRANSPORT}
)

# =========================
# TRANSPORT LAYER
# =========================

option(USE_SOCKET "Use socket transport" ON)

if(USE_SOCKET)
    add_library(remote_transport STATIC 
    ${SRC_TRANSPORT}/sockets.c )
else()
    add_library(remote_transport STATIC 
    ${SRC_TRANSPORT}/uart.c)
endif()

target_include_directories(remote_transport PUBLIC
    ${SRC_TRANSPORT}
    ${SRC_LIB}
)

# =========================
# APP
# =========================

add_executable(remote_control
    ${SRC_APP}/main.c
)

target_link_libraries(remote_control PRIVATE
    remote_core
    remote_transport
)

target_include_directories(remote_control PRIVATE
    ${SRC_LIB}
    ${SRC_TRANSPORT}
)

# =========================
# TESTS
# =========================

add_subdirectory(${SRC_UNIT_TESTS})