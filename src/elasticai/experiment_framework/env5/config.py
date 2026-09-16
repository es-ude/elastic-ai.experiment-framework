from enum import IntEnum

BYTE_ORDER = "little"


class TaskDefinitionIds(IntEnum):
    FPGA_INIT = 0x3
    FPGA_POWER_ON = 0x4
    FPGA_POWER_OFF = 0x5
    FPGA_WRITE_TO_FLASH = 0x6
    FPGA_READ_SKELETON_ID = 0x7
    FPGA_PREDICT = 0x8
    
