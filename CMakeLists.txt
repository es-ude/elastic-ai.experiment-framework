cmake_minimum_required(VERSION 3.10)

project(embedded_remote_control C)

enable_testing()

set(SRC_DIR_SERVER 
    ${CMAKE_SOURCE_DIR}/src/elasticai/experiment_framework/remote_control/embedded_side
)

set(SRC_DIR_TEST 
    ${CMAKE_SOURCE_DIR}/tests/system
)

configure_file(
    ${SRC_DIR_SERVER}/start_server.sh
    ${CMAKE_BINARY_DIR}/start_server.sh
    FILE_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE
)

add_library(embedded_common
        ${SRC_DIR_SERVER}/connection_manager.c
        ${SRC_DIR_SERVER}/frame_builder.c
        ${SRC_DIR_SERVER}/ThreadSafeQueue.c
        ${SRC_DIR_SERVER}/sender.c
        ${SRC_DIR_SERVER}/receiver.c       
        ${SRC_DIR_SERVER}/task_manager.c
        ${SRC_DIR_SERVER}/msg_handler.c
        
        ${SRC_DIR_SERVER}/embedded_functions.c
        )


add_executable(
    embedded_remote_control
    ${SRC_DIR_SERVER}/main.c
    
)

target_link_libraries(embedded_remote_control
                        PRIVATE embedded_common)


add_executable(
    embedded_remote_control_test
    ${SRC_DIR_TEST}/embedded_test.c
)


target_link_libraries(embedded_remote_control_test
                        PRIVATE embedded_common)









add_test(NAME start_server
    COMMAND "./start_server.sh"
)
set_tests_properties(start_server PROPERTIES
    FIXTURES_SETUP server_fixture
)


add_test(
    NAME System_test
    COMMAND embedded_remote_control_test 0 abc
)
set_tests_properties(System_test PROPERTIES
    FIXTURES_REQUIRED server_fixture
)


add_test(NAME stop_server
    COMMAND bash -c "kill $(cat server.pid) || true; rm server.pid"
)
set_tests_properties(stop_server PROPERTIES
    FIXTURES_CLEANUP server_fixture
)