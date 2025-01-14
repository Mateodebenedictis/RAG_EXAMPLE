import logging
import json
from pydantic import BaseModel
from typing import Dict

_logger = logging.getLogger(__file__)
_formatter = logging.Formatter("Analytics user event: %(name)s - %(message)s")
_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)
_logger.addHandler(_handler)
_logger.setLevel(logging.INFO)


class Event(BaseModel):
    name: str
    data: Dict[str, str]


def trackEvent(event: Event):
    _logger.info("%s: %s", event.name, json.dumps(event.data))
