"""两期比较：按（话题 × 渠道 × 指标）切片判断可比性，不做跨指标总分。

只有口径一致、两期都有记录的切片才可比较；其余切片明确标注原因
（口径变化、渠道覆盖缺失、指标含义不明），由复盘报告如实呈现。
"""

from collections import defaultdict
from dataclasses import dataclass

# 切片比较状态
COMPARABLE = "comparable"  # 两期口径一致，可比较
DEFINITION_CHANGED = "definition-changed"  # 两期口径版本不同（含期内混用多版本）
MISSING_IN_START = "missing-in-start"  # 起始周期无记录（渠道覆盖或内容范围变化）
MISSING_IN_END = "missing-in-end"  # 结束周期无记录
METRIC_UNKNOWN = "metric-unknown"  # 未标注口径或版本，数值含义不明

GAP_STATUSES = (DEFINITION_CHANGED, MISSING_IN_START, MISSING_IN_END, METRIC_UNKNOWN)


@dataclass(frozen=True)
class SliceComparison:
    """一个（话题 × 渠道 × 指标）切片在两期之间的比较结果。"""

    topic: str
    source_id: str
    metric_id: str | None
    status: str
    start_value: float | None = None
    end_value: float | None = None
    start_versions: tuple[str, ...] = ()
    end_versions: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class PeriodComparison:
    """两期比较结果：所有切片及其可比性状态。"""

    start: tuple[int, int]
    end: tuple[int, int]
    region: str | None
    slices: tuple[SliceComparison, ...]

    @property
    def comparable(self):
        return tuple(s for s in self.slices if s.status == COMPARABLE)

    @property
    def gaps(self):
        return tuple(s for s in self.slices if s.status != COMPARABLE)

    def rollup(self):
        """按 (topic, metric_id) 合计可比切片，并列出被排除的来源及原因。

        合计只在同一指标口径内进行，不跨指标相加；不可比切片只出现在
        excluded 中，不进入合计。
        """
        out = {}
        for s in self.slices:
            key = (s.topic, s.metric_id)
            entry = out.setdefault(
                key,
                {"start_value": 0.0, "end_value": 0.0, "sources": [], "excluded": []},
            )
            if s.status == COMPARABLE:
                entry["start_value"] += s.start_value
                entry["end_value"] += s.end_value
                entry["sources"].append(s.source_id)
            else:
                entry["excluded"].append((s.source_id, s.status))
        return {
            key: {
                "start_value": entry["start_value"],
                "end_value": entry["end_value"],
                "sources": tuple(sorted(entry["sources"])),
                "excluded": tuple(sorted(entry["excluded"])),
            }
            for key, entry in sorted(
                out.items(), key=lambda item: (item[0][0], item[0][1] or "")
            )
        }


def _classify(metric_id, in_start, in_end, start_versions, end_versions):
    if not in_start:
        return MISSING_IN_START, "该切片在起始周期没有记录"
    if not in_end:
        return MISSING_IN_END, "该切片在结束周期没有记录"
    if metric_id is None:
        return METRIC_UNKNOWN, "记录未标注指标口径，无法说明数值含义"
    if not start_versions or not end_versions:
        return METRIC_UNKNOWN, "记录缺少口径版本，无法确认两期口径一致"
    if len(start_versions) > 1 or len(end_versions) > 1:
        return DEFINITION_CHANGED, (
            f"同一周期内混用多个口径版本："
            f"{'+'.join(start_versions)} → {'+'.join(end_versions)}"
        )
    if start_versions != end_versions:
        return DEFINITION_CHANGED, (
            f"两期口径版本不同：{start_versions[0]} → {end_versions[0]}"
        )
    return COMPARABLE, ""


def compare_periods(observations, start, end, *, region=None):
    """比较两个 (year, month) 周期，返回 PeriodComparison。

    每个（话题 × 渠道 × 指标）切片独立判断可比性；region 参数按观察记录
    的地区过滤。
    """
    periods = ((start[0], start[1]), (end[0], end[1]))
    # buckets[slot][(topic, source_id, metric_id)] = [合计值, 口径版本集合]
    buckets = (
        defaultdict(lambda: [0.0, set()]),
        defaultdict(lambda: [0.0, set()]),
    )
    for obs in observations:
        if region is not None and obs.region != region:
            continue
        key = (obs.observed_on.year, obs.observed_on.month)
        if key not in periods:
            continue
        slot = periods.index(key)
        bucket = buckets[slot][(obs.topic, obs.source_id, obs.metric_id)]
        bucket[0] += obs.value
        if obs.metric_version is not None:
            bucket[1].add(obs.metric_version)

    slices = []
    slice_keys = set(buckets[0]) | set(buckets[1])
    for topic, source_id, metric_id in sorted(
        slice_keys, key=lambda k: (k[0], k[1], k[2] or "")
    ):
        in_start = (topic, source_id, metric_id) in buckets[0]
        in_end = (topic, source_id, metric_id) in buckets[1]
        start_value = buckets[0][(topic, source_id, metric_id)][0] if in_start else None
        end_value = buckets[1][(topic, source_id, metric_id)][0] if in_end else None
        start_versions = (
            tuple(sorted(buckets[0][(topic, source_id, metric_id)][1]))
            if in_start
            else ()
        )
        end_versions = (
            tuple(sorted(buckets[1][(topic, source_id, metric_id)][1]))
            if in_end
            else ()
        )
        status, detail = _classify(
            metric_id, in_start, in_end, start_versions, end_versions
        )
        slices.append(
            SliceComparison(
                topic=topic,
                source_id=source_id,
                metric_id=metric_id,
                status=status,
                start_value=start_value,
                end_value=end_value,
                start_versions=start_versions,
                end_versions=end_versions,
                detail=detail,
            )
        )
    return PeriodComparison(
        start=start, end=end, region=region, slices=tuple(slices)
    )
