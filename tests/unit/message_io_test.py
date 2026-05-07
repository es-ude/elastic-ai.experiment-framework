

from elasticai.experiment_framework.remote_control.pc_side.protocol.commands import Command
from elasticai.experiment_framework.remote_control.pc_side.protocol.message import Message


def make_return(payload: bytes) -> bytes:
    """Build a fake RETURN message from the board"""
    return Message(Command.RETURN, payload).to_bytes()
