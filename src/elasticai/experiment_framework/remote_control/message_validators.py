from collections.abc import Callable
from functools import partial

from .commands import Command
from .constants import NackErrorCode
from .exceptions import InvalidCommandPayloadError

PayloadValidator = Callable[[bytes], None]


def validate_length(payload: bytes, *, expected: int) -> None:
    if len(payload) != expected:
        raise InvalidCommandPayloadError(
            f"Expected {expected} bytes, got {len(payload)}"
        )


def validate_error_code(payload: bytes) -> None:
    try:
        NackErrorCode(payload[0])
    except ValueError as exc:
        raise InvalidCommandPayloadError(
            f"Invalid NACK error code: {payload[0]}"
        ) from exc


PAYLOAD_VALIDATORS: dict[Command, tuple[PayloadValidator, ...]] = {
    Command.ACK: (partial(validate_length, expected=0),),
    Command.NACK: (
        partial(validate_length, expected=1),
        validate_error_code,
    ),
    Command.RETURN: (
        partial(validate_length, expected=1),
    ),
}


def validate_payload(command: Command, payload: bytes) -> None:
    for validator in PAYLOAD_VALIDATORS.get(command, ()):
        validator(payload)
