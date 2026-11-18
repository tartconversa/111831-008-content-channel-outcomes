from datetime import date

from .records import MetricDefinition


class DefinitionRegistry:
    """按 (metric_id, version) 登记的指标口径注册表。

    同一 (metric_id, version) 不允许登记不同内容：口径变化必须发新版本，
    这样已留档报告引用的口径不会被悄悄改写。
    """

    def __init__(self, definitions=()):
        self._definitions = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition):
        key = (definition.metric_id, definition.version)
        existing = self._definitions.get(key)
        if existing is not None and existing != definition:
            raise ValueError(
                f"口径 {key} 已登记且内容不同；口径变化请使用新版本号"
            )
        self._definitions[key] = definition
        return definition

    def get(self, metric_id, version):
        return self._definitions.get((metric_id, version))

    def versions(self, metric_id):
        return tuple(
            sorted(version for (mid, version) in self._definitions if mid == metric_id)
        )

    def current(self, metric_id, on=None):
        """返回 on 当日有效的口径版本；无有效版本时返回 None。"""
        on = on or date.today()
        candidates = [
            definition
            for (mid, _), definition in self._definitions.items()
            if mid == metric_id
            and (definition.valid_from is None or definition.valid_from <= on)
            and (definition.valid_to is None or definition.valid_to >= on)
        ]
        if not candidates:
            return None
        return max(
            candidates, key=lambda d: (d.valid_from or date.min, d.version)
        )

    def snapshot(self, refs=None):
        """返回 {ref: MetricDefinition} 副本，用于随报告留档。

        refs 为 (metric_id, version) 可迭代对象；缺省快照全部已登记口径。
        未登记的 ref 静默跳过（报告中相应切片会标注“定义未登记”）。
        """
        if refs is None:
            return dict(self._definitions)
        return {
            ref: self._definitions[ref]
            for ref in sorted(set(refs))
            if ref in self._definitions
        }
