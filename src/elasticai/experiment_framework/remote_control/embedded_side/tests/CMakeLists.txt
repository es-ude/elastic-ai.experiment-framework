cmake_minimum_required(VERSION 3.10)

project(embedded_remote_control_test C)

add_executable(embedded_remote_control_test embedded_test.c ../sockets.c ../frame_builder.c)