target_sources(remote_lib PRIVATE
    task_definitions.c
    task_definition_host.c
)

if (ELASTIC_AI_TARGET STREQUAL "ENV5_2")
    set(BITSTREAM_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../env5_top_reconfig.bin")
    if (EXISTS "${BITSTREAM_PATH}")
        file(READ "${BITSTREAM_PATH}" FPGA_BITSTREAM_HEX HEX)
        string(REGEX REPLACE "([0-9a-fA-F][0-9a-fA-F])" "0x\\1, " FPGA_BITSTREAM_BYTES "${FPGA_BITSTREAM_HEX}")
        string(REGEX REPLACE ", $" "" FPGA_BITSTREAM_BYTES "${FPGA_BITSTREAM_BYTES}")
        file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/embedded_fpga_bitstream.h"
            "#pragma once\n"
            "#include <stddef.h>\n"
            "static const unsigned char fpga_bitstream[] = {${FPGA_BITSTREAM_BYTES}};\n"
            "static const size_t fpga_bitstream_size = sizeof(fpga_bitstream) / sizeof(fpga_bitstream[0]);\n")
    else()
        file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/embedded_fpga_bitstream.h"
            "#pragma once\n"
            "#include <stddef.h>\n"
            "static const unsigned char fpga_bitstream[] = {0xff, 0xf0, 0x0f};\n"
            "static const size_t fpga_bitstream_size = 3;\n")
    endif()

    target_include_directories(remote_lib PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
    target_sources(remote_lib PRIVATE
        task_definitions_pico.c
    )
endif()