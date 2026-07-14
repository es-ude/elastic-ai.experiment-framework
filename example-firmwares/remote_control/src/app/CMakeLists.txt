add_executable(remote_control
    main.c
)

    
if(ELASTIC_AI_TARGET STREQUAL "ENV5_2")

    target_link_libraries(remote_control PRIVATE

        pico_stdlib

    )


    pico_enable_stdio_usb(
        remote_control
        1
    )


    pico_enable_stdio_uart(
        remote_control
        0
    )


    set_target_properties(remote_control PROPERTIES
        SUFFIX ".elf"
    )


    pico_add_extra_outputs(
        remote_control
    )



endif()

target_link_libraries(remote_control PUBLIC
        remote_lib
    )

