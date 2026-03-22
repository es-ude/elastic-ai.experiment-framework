add_library(experiment experiment/fpgaPowerSensor.c experiment/I2cPico.c
        experiment/SpiPico.c
        experiment/Middleware.c)
target_include_directories(experiment PUBLIC ${CMAKE_CURRENT_LIST_DIR})

add_library(env5_fpga experiment/PicoFpga.c)
target_include_directories(env5_fpga PUBLIC ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(env5_fpga Pico::hardware_gpio Pico::pico_runtime Pico::pico_stdlib)

add_library(pico_spi experiment/SpiPico.c)
target_include_directories(pico_spi PUBLIC ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(pico_spi Pico::hardware_spi Gpio Pico::pico_runtime)

add_library(fpga_middleware experiment/Middleware.c)
target_include_directories(fpga_middleware PUBLIC ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(fpga_middleware PRIVATE pico_spi)

target_link_libraries(experiment
        Common
        EnV5HwConfiguration
        EnV5HwController
        Flash
        Gpio
        UsbProtocol
        Middleware
        CException
        Pac193x
        I2c
        Pico::pico_stdlib
        Pico::pico_stdio_usb
        Pico::pico_time
        Pico::hardware_spi
        Pico::hardware_i2c
)

add_subdirectory(experiment/remote_control_protocol)