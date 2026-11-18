from dataclasses import dataclass
from datetime import date

# 传播关系取值：
# - origin：某条传播路径上的首条记录；
# - reshare：同一路径上的下游扩散，path_root 指向路径中已有的记录；
# - response：独立响应，不属于任何被追踪的传播路径。
RELATIONS = ("origin", "reshare", "response")


@dataclass(frozen=True)
class Source:
    """一个渠道账号：观察数据的来源。"""

    source_id: str
    region: str
    language: str
    active: bool = True

    @classmethod
    def from_dict(cls, row):
        return cls(**dict(row))


@dataclass(frozen=True)
class MetricDefinition:
    """渠道回传指标的口径定义，按 (metric_id, version) 登记。

    behavior：数值代表的行为，如 read / share / comment / visit；
    window_days：观察窗口（天）；
    audience_scope：统计的受众范围，如 all-users、followers。

    同一 (metric_id, version) 登记后不可变；口径变化必须登记为新版本，
    以保证已留档的复盘仍可按当时口径解读。
    """

    metric_id: str
    version: str
    behavior: str
    window_days: int
    audience_scope: str
    unit: str = "count"
    note: str = ""
    valid_from: date | None = None
    valid_to: date | None = None

    @classmethod
    def from_dict(cls, row):
        data = dict(row)
        for key in ("valid_from", "valid_to"):
            if data.get(key) is not None:
                data[key] = date.fromisoformat(data[key])
        return cls(**data)


@dataclass(frozen=True)
class Observation:
    """一条观察记录。

    metric_id / metric_version 标明数值的口径（含义、窗口、受众范围）；
    两者都缺失时，该记录无法说明数值代表什么行为，比较时按 metric-unknown 处理。

    content_id / relation / path_root 描述传播关系，见 RELATIONS。
    """

    observation_id: str
    source_id: str
    observed_on: date
    topic: str
    value: float
    region: str = "global"
    metric_id: str | None = None
    metric_version: str | None = None
    content_id: str | None = None
    relation: str = "origin"
    path_root: str | None = None

    def __post_init__(self):
        if self.relation not in RELATIONS:
            raise ValueError(f"未知传播关系：{self.relation!r}（可选：{RELATIONS}）")

    @property
    def metric_ref(self):
        """(metric_id, version) 对；任一缺失时返回 None，表示口径不明。"""
        if self.metric_id is None or self.metric_version is None:
            return None
        return (self.metric_id, self.metric_version)

    @classmethod
    def from_dict(cls, row):
        data = dict(row)
        data["observed_on"] = date.fromisoformat(data["observed_on"])
        return cls(**data)
