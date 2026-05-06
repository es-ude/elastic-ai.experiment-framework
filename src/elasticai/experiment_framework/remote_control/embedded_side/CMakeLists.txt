cmake_minimum_required(VERSION 3.10)

project(embedded_remote_control C)

add_executable(embedded_remote_control embedded_protocol.c sockets.c embedded_functions.c task_manager.c frame_builder.c)