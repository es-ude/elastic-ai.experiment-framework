from enum import IntEnum

BYTE_ORDER = "little"


class TaskDefinitionIds(IntEnum):
    FPGA_INIT = 0x0
    FPGA_POWER_ON = 0x1
    FPGA_POWER_OFF = 0x2
    FPGA_WRITE_TO_FLASH = 0x3
    FPGA_READ_SKELETON_ID = 0x4
    FPGA_PREDICT = 0x5
    
