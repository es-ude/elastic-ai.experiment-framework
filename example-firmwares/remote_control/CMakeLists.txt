cmake_minimum_required(VERSION 3.10)
project(embedded_remote_control C)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

enable_testing()

# =========================
# PATHS
# =========================

set(SRC_LIB        ${CMAKE_SOURCE_DIR}/src/lib)
set(SRC_USER_CODE  ${CMAKE_SOURCE_DIR}/src/user_code)
set(SRC_INTERFACES ${CMAKE_SOURCE_DIR}/src/interfaces)
set(SRC_APP        ${CMAKE_SOURCE_DIR}/src/app)
set(SRC_TRANSPORT  ${CMAKE_SOURCE_DIR}/src/transport)
set(SRC_TESTS      ${CMAKE_SOURCE_DIR}/tests/unit)


# =========================
# INIT
# =========================

if(PLATFORM STREQUAL "host")

    message(STATUS "Building for HOST")

else()

    message(FATAL_ERROR "Unknown PLATFORM: ${PLATFORM}")

endif()


# =========================
# CORE LIB
# =========================

add_library(remote_core

    ${SRC_USER_CODE}/task_definitions.c
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
    ${SRC_INTERFACES}
    ${SRC_USER_CODE}
)


# =========================
# SANITIZER
# =========================

if(ENABLE_ASAN AND PLATFORM STREQUAL "host")

    message(STATUS "AddressSanitizer enabled")

    target_compile_options(remote_core PRIVATE

        -fsanitize=address
        -fno-omit-frame-pointer

    )

    target_link_options(remote_core INTERFACE

        -fsanitize=address

    )

endif()


# =========================
# TRANSPORT IMPLEMENTATION
# =========================

if(PLATFORM STREQUAL "host")

    target_sources(remote_core PRIVATE

        ${SRC_TRANSPORT}/sockets.c

    )


endif()


# =========================
# APPLICATION
# =========================

if(PLATFORM STREQUAL "host")


    add_executable(remote_control

        ${SRC_APP}/main.c

    )


    target_link_libraries(remote_control PRIVATE

        remote_core

    )



endif()


# =========================
# TESTS
# =========================

if(PLATFORM STREQUAL "host")

    add_subdirectory(
        ${SRC_TESTS}
    )

endif()