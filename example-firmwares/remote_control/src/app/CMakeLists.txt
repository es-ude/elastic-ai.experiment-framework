add_executable(remote_control
    main.c
)
if(ELASTIC_AI_TARGET STREQUAL "ENV5_2")
    set(ENV5_BITSTREAM
        "${CMAKE_CURRENT_SOURCE_DIR}/../user_code/env5_top_reconfig.bin"
    )

    set(ENV5_BITSTREAM_OBJ
        "${CMAKE_CURRENT_BINARY_DIR}/env5_top_reconfig.o"
    )

    add_custom_command(
        OUTPUT "${ENV5_BITSTREAM_OBJ}"

        COMMAND ${CMAKE_OBJCOPY}
            -I binary
            -O elf32-littlearm
            -B arm
            --rename-section
            .data=.rodata,alloc,load,readonly,data,contents
            "env5_top_reconfig.bin"
            "${ENV5_BITSTREAM_OBJ}"

        DEPENDS "${ENV5_BITSTREAM}"

        WORKING_DIRECTORY
            "${CMAKE_CURRENT_SOURCE_DIR}/../user_code"

        VERBATIM
    )

    target_sources(remote_control PRIVATE
        "${ENV5_BITSTREAM_OBJ}"
    )

    target_link_libraries(remote_control PRIVATE
        pico_stdlib
    )

    pico_enable_stdio_usb(remote_control 1)
    pico_enable_stdio_uart(remote_control 0)

    set_target_properties(remote_control PROPERTIES
        SUFFIX ".elf"
    )

    pico_add_extra_outputs(remote_control)
endif()

target_link_libraries(remote_control PUBLIC
    remote_lib
)