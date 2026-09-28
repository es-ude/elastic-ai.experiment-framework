import logging

DISPLAY_NAMES = {
    "elasticai.experiment_framework.remote_control.traffic.message.incoming": "RX",
    "elasticai.experiment_framework.remote_control.traffic.message.outgoing": "TX",
    "elasticai.experiment_framework.remote_control.traffic.raw.incoming": "RAW-RX",
    "elasticai.experiment_framework.remote_control.traffic.raw.outgoing": "RAW-TX",
}

DISABLED_LOGGERS = {
    "elasticai.experiment_framework.remote_control.traffic.raw.incoming",
    "elasticai.experiment_framework.remote_control.traffic.raw.outgoing",
}


class ShortNameFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        name = DISPLAY_NAMES.get(record.name)

        if name is not None:
            return f"{record.levelname:<8} {name:<7} {record.getMessage()}"

        return record.getMessage()


class ExcludeRawTraffic(logging.Filter):
    def __init__(self, show_raw: bool = False):
        super().__init__()
        self.show_raw = show_raw

    def filter(self, record: logging.LogRecord) -> bool:
        if self.show_raw:
            return True

        return not record.name.startswith(
            "elasticai.experiment_framework.remote_control.traffic.raw."
        )


def configure_logging(
    level: int = logging.INFO,
    show_raw: bool = False,
) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ShortNameFormatter())
    handler.addFilter(ExcludeRawTraffic(show_raw))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
