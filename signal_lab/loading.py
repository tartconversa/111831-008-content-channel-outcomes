"""从 JSON 文件加载来源、口径定义与观察记录。"""

import json
from pathlib import Path

from .records import MetricDefinition, Observation, Source


def _load_rows(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_sources(path):
    return tuple(Source.from_dict(row) for row in _load_rows(path))


def load_definitions(path):
    return tuple(MetricDefinition.from_dict(row) for row in _load_rows(path))


def load_observations(path):
    return tuple(Observation.from_dict(row) for row in _load_rows(path))
