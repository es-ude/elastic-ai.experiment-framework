set(TESTS
    test_receiver.c
    test_sender.c
    test_ringbuffer.c
    test_task_manager.c
    test_msg_handler.c
)

foreach(test ${TESTS})
    get_filename_component(name ${test} NAME_WE)

    add_executable(${name}_tests
        ${test}
        unity.c
    )

    target_link_libraries(${name}_tests PRIVATE
        remote_core
    )

    target_include_directories(${name}_tests PRIVATE
        ${CMAKE_SOURCE_DIR}/tests/unit/test_header
        ${SRC_LIB}
        ${SRC_TRANSPORT}
    )

    add_test(NAME ${name}_tests COMMAND ${name}_tests)
endforeach()