add_executable(env5_experiment_firmware 
        experiment.c
        config.c
)

add_subdirectory(libs)
add_subdirectory(tests)

target_link_libraries(env5_experiment_firmware
        env5_fpga
        pico_spi
        fpga_middleware
        Common
        EnV5HwConfiguration
        EnV5HwController
        Flash
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
create_enV5_executable(env5_experiment_firmware)
