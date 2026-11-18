"""复盘报告留档：保存原始读数、当时口径快照与有范围的观察陈述。

陈述一律为“在……渠道/受众范围/观察窗口内观察到……”的观察句式；
报告固定附带边界声明：同时发生的转发或访问不能据此归因于某一内容。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .analysis import (
    COMPARABLE,
    DEFINITION_CHANGED,
    METRIC_UNKNOWN,
    MISSING_IN_END,
    MISSING_IN_START,
)
from .records import MetricDefinition

BEHAVIOR_LABELS = {
    "read": "阅读",
    "share": "转发",
    "comment": "评论",
    "visit": "访问",
}

FIELD_LABELS = {
    "behavior": "行为含义",
    "window_days": "观察窗口（天）",
    "audience_scope": "受众范围",
    "unit": "单位",
    "note": "说明",
}

# 每份报告固定附带的边界声明
SCOPE_CAVEAT = (
    "以上均为对应渠道、受众范围与观察窗口内的观察记录；"
    "同一内容在不同账号间的转发属于同一条传播路径，独立响应单独计数；"
    "同时发生的转发或访问不能据此归因于某一内容。"
)


@dataclass(frozen=True)
class Reading:
    """一条留档读数：某切片在某周期的原始合计值与当时口径版本。"""

    topic: str
    source_id: str
    metric_id: str | None
    versions: tuple[str, ...]
    period: tuple[int, int]
    value: float


@dataclass(frozen=True)
class AnalysisReport:
    """留档的复盘：原始读数 + 当时口径快照 + 可比结论与缺失说明。"""

    report_id: str
    title: str
    period_start: tuple[int, int]
    period_end: tuple[int, int]
    source_ids: tuple[str, ...]
    readings: tuple[Reading, ...]
    definitions: dict[tuple[str, str], MetricDefinition]
    statements: tuple[str, ...]
    gaps: tuple[str, ...]
    caveats: tuple[str, ...] = (SCOPE_CAVEAT,)
    created_at: str = ""


def _period_label(period):
    year, month = period
    return f"{year} 年 {month} 月"


def _fmt(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def definition_delta(old, new):
    """两个口径版本之间的字段差异（用于说明“口径变了什么”）。"""
    changes = []
    for field_name, label in FIELD_LABELS.items():
        old_value = getattr(old, field_name)
        new_value = getattr(new, field_name)
        if old_value != new_value:
            changes.append(f"{label}：{old_value} → {new_value}")
    return tuple(changes)


def _behavior_label(definition, metric_id):
    if definition is None:
        return metric_id or "未标注指标"
    return BEHAVIOR_LABELS.get(definition.behavior, definition.behavior)


def render_statement(slice, definitions, start, end):
    """可比切片的观察陈述：带渠道、受众范围、窗口与口径版本。"""
    version = slice.start_versions[0] if slice.start_versions else None
    definition = definitions.get((slice.metric_id, version)) if version else None
    behavior = _behavior_label(definition, slice.metric_id)
    if definition is not None:
        scope = (
            f"{slice.source_id} 渠道（受众范围 {definition.audience_scope}，"
            f"观察窗口 {definition.window_days} 天，"
            f"口径 {definition.metric_id} {definition.version}）"
        )
    else:
        scope = (
            f"{slice.source_id} 渠道"
            f"（口径 {slice.metric_id} {version or '未标注版本'}，定义未登记）"
        )
    return (
        f"在 {scope} 观察到「{slice.topic}」的{behavior}："
        f"{_period_label(start)}为 {_fmt(slice.start_value)}，"
        f"{_period_label(end)}为 {_fmt(slice.end_value)}。"
    )


def render_gap(slice, definitions, start, end):
    """不可比切片的说明：缺失或口径变化，如实标注。"""
    label = (
        f"{slice.source_id} 渠道「{slice.topic}」的 "
        f"{slice.metric_id or '未标注指标'}"
    )
    if slice.status == MISSING_IN_START:
        return (
            f"{label} 在{_period_label(start)}无记录"
            f"（{_period_label(end)}为 {_fmt(slice.end_value)}），未纳入两期比较。"
        )
    if slice.status == MISSING_IN_END:
        return (
            f"{label} 在{_period_label(end)}无记录"
            f"（{_period_label(start)}为 {_fmt(slice.start_value)}），未纳入两期比较。"
        )
    if slice.status == METRIC_UNKNOWN:
        return f"{label} 未标注指标口径或版本，无法说明数值含义，未纳入两期比较。"
    if slice.status == DEFINITION_CHANGED:
        start_version = "+".join(slice.start_versions) or "未标注"
        end_version = "+".join(slice.end_versions) or "未标注"
        delta = ""
        old = definitions.get((slice.metric_id, slice.start_versions[0])) if len(slice.start_versions) == 1 else None
        new = definitions.get((slice.metric_id, slice.end_versions[0])) if len(slice.end_versions) == 1 else None
        if old is not None and new is not None:
            changes = definition_delta(old, new)
            if changes:
                delta = f"（{'；'.join(changes)}）"
        return (
            f"{label} 的口径从 {start_version} 变为 {end_version}{delta}，"
            f"两期数值不直接可比"
            f"（{_period_label(start)}为 {_fmt(slice.start_value)}，"
            f"{_period_label(end)}为 {_fmt(slice.end_value)}）。"
        )
    raise ValueError(f"未知切片状态：{slice.status!r}")


def _readings(comparison):
    readings = []
    for slice in comparison.slices:
        if slice.start_value is not None:
            readings.append(
                Reading(
                    topic=slice.topic,
                    source_id=slice.source_id,
                    metric_id=slice.metric_id,
                    versions=slice.start_versions,
                    period=comparison.start,
                    value=slice.start_value,
                )
            )
        if slice.end_value is not None:
            readings.append(
                Reading(
                    topic=slice.topic,
                    source_id=slice.source_id,
                    metric_id=slice.metric_id,
                    versions=slice.end_versions,
                    period=comparison.end,
                    value=slice.end_value,
                )
            )
    return tuple(readings)


def create_report(report_id, title, comparison, *, registry=None, definitions=None):
    """根据 PeriodComparison 生成留档报告。

    definitions 为 {(metric_id, version): MetricDefinition}；传入 registry 时
    自动快照比较中引用到的全部口径版本。快照随报告保存，之后注册表更新
    不影响已留档报告。
    """
    if definitions is None:
        if registry is not None:
            refs = set()
            for slice in comparison.slices:
                if slice.metric_id is None:
                    continue
                for version in slice.start_versions + slice.end_versions:
                    refs.add((slice.metric_id, version))
            definitions = registry.snapshot(refs)
        else:
            definitions = {}
    definitions = dict(definitions)

    return AnalysisReport(
        report_id=report_id,
        title=title,
        period_start=comparison.start,
        period_end=comparison.end,
        source_ids=tuple(sorted({s.source_id for s in comparison.slices})),
        readings=_readings(comparison),
        definitions=definitions,
        statements=tuple(
            render_statement(s, definitions, comparison.start, comparison.end)
            for s in comparison.comparable
        ),
        gaps=tuple(
            render_gap(s, definitions, comparison.start, comparison.end)
            for s in comparison.gaps
        ),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
