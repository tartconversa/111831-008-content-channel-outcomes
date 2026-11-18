# 传播渠道效果观察

这个 Python 项目整理各海外传播渠道回传的观察记录，按渠道、受众范围与指标口径做两期比较，追踪传播路径与独立响应，并生成供研究人员复核的留档报告。指标口径按版本登记，报告保留原始读数与当时口径；结果只支持对应范围内的观察，不做跨指标总分与传播因果归因。详见 `docs/analysis-notes.md`。

## 用法

```python
from signal_lab import DefinitionRegistry, compare_periods, create_report, summarize_propagation
from signal_lab.loading import load_definitions, load_observations

observations = load_observations("fixtures/observations.json")
registry = DefinitionRegistry(load_definitions("fixtures/definitions.json"))

comparison = compare_periods(observations, (2026, 10), (2026, 11))
report = create_report("review-2026-11", "两期复盘", comparison, registry=registry)

report.statements  # 可比切片的观察陈述（带渠道、受众范围、窗口、口径版本）
report.gaps        # 缺失与口径变化说明
summarize_propagation(observations)  # 每个内容的传播路径与独立响应
```

## 开发

需要 Python 3.11 或更高版本。安装开发依赖：`python -m pip install -e .`。

运行测试：`python -m unittest discover -s tests -v`。
构建发行包：`python -m build`。
