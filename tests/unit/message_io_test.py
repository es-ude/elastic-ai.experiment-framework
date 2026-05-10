from typing import Self


from elasticai.experiment_framework.remote_control_v2.commands import Command
from elasticai.experiment_framework.remote_control_v2.message import Message



def make_return(payload: bytes) -> bytes:
    """Build a fake RETURN message from the board"""
    return Message(Command.RETURN, payload).to_bytes()

