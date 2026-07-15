if(ELASTIC_AI_TARGET STREQUAL "HOST")

    target_sources(remote_lib PRIVATE
        sockets.c
    )

    target_compile_definitions(remote_lib PUBLIC
        ENABLE_LOGGING
    )

elseif(ELASTIC_AI_TARGET STREQUAL "ENV5_2")

    target_sources(remote_lib PRIVATE
        usb_pico.c
    )
    
    target_link_libraries(remote_lib PUBLIC
            pico_stdlib
        )
    
    endif()

    