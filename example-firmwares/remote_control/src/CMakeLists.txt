add_library(remote_lib STATIC)

target_include_directories(remote_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/lib
    ${CMAKE_CURRENT_SOURCE_DIR}/interfaces
    ${CMAKE_CURRENT_SOURCE_DIR}/transport
    ${CMAKE_CURRENT_SOURCE_DIR}/hardware_functions
    ${CMAKE_CURRENT_SOURCE_DIR}/user_code
    ${CMAKE_CURRENT_SOURCE_DIR}/config
)

add_subdirectory(lib)
add_subdirectory(transport)

add_subdirectory(user_code)


if (ELASTIC_AI_TARGET STREQUAL "ENV5_2")
    add_subdirectory(hardware_functions)
    add_subdirectory(config)
    target_link_libraries(remote_lib
        PUBLIC
        Common
        Middleware
        Flash
        EnV5HwController
        EnV5HwConfiguration
        Spi
        UsbProtocol
        Gpio
        pico_stdlib
        hardware_spi
        pico_stdio_usb
    )
endif()


if(ELASTIC_AI_TARGET STREQUAL "HOST")
    target_compile_definitions(remote_lib PUBLIC PLATFORM_HOST)
elseif(ELASTIC_AI_TARGET STREQUAL "ENV5_2")
    target_compile_definitions(remote_lib PUBLIC PLATFORM_PICO)
endif()

# =========================
# SANITIZER
# =========================

if(ENABLE_ASAN AND PLATFORM STREQUAL "host")

    message(STATUS "AddressSanitizer enabled")

    target_compile_options(remote_lib INTERFACE

        -fsanitize=address
        -fno-omit-frame-pointer

    )

    target_link_options(remote_lib INTERFACE

        -fsanitize=address

    )

endif()

# =========================
# APPLICATION
# =========================

add_subdirectory(app)


