# 分析口径

本项目整理各海外传播渠道回传的观察记录，生成供研究复核的两期比较与复盘留档。核心原则：数值只有在明确的渠道、受众范围与指标口径下才可解释；项目不做跨指标总分，也不做传播因果归因。

## 记录模型

- `Source`：渠道账号（地区、语言、是否活跃）。
- `MetricDefinition`：指标口径，按 `(metric_id, version)` 登记。`behavior` 说明数值代表的行为（read / share / comment / visit），`window_days` 为观察窗口，`audience_scope` 为统计的受众范围。
- `Observation`：一条观察记录。`metric_id` / `metric_version` 标明数值口径；`content_id`、`relation`、`path_root` 描述传播关系。

## 指标口径登记

口径由 `DefinitionRegistry` 按 `(metric_id, version)` 登记。同一版本号不允许登记不同内容——口径变化（窗口、受众范围、行为含义等）必须发新版本。这样已留档复盘引用的口径不会被改写。

## 传播路径

- `relation=origin`：某条传播路径的首条记录；
- `relation=reshare`：同一路径上的下游扩散，`path_root` 指向路径中已有记录（可传递解析到起点）；
- `relation=response`：独立响应，不属于任何被追踪路径。

`path_root` 指向缺失记录（或未指明）时，该记录标记为 dangling（起点缺失），不计入任何路径。路径只描述扩散结构——几条路径、几个独立响应、涉及哪些渠道；同一路径上的数值不跨记录累加。

## 两期比较的可比性

`compare_periods` 按（话题 × 渠道 × 指标）切片比较两个 `(年, 月)` 周期，每个切片标记为：

- `comparable`：两期都有记录且口径版本一致；
- `definition-changed`：两期口径版本不同，或同一周期内混用多个版本；
- `missing-in-start` / `missing-in-end`：某一期无记录（渠道覆盖或内容范围变化）；
- `metric-unknown`：未标注口径或版本，数值含义不明。

`rollup()` 只合计 `comparable` 切片，且按（话题 × 指标）分别合计，不跨指标相加；不可比切片只列入 `excluded`，不进入合计。

## 复盘留档

`create_report` 把以下内容一并存入 `AnalysisReport`：

- 各切片的原始读数（含当时口径版本）；
- 比较中引用到的 `MetricDefinition` 快照——之后注册表更新不影响已留档报告；
- 可比切片的观察陈述与不可比切片的缺失/口径变化说明（口径变化附字段级差异）。

## 表述边界

报告陈述一律为“在……渠道（受众范围、观察窗口、口径版本）观察到……”的观察句式。同一内容在不同账号间的转发属于同一条传播路径，不当作独立响应；同时发生的转发或访问不能据此归因于某一内容。每份报告固定附带该边界声明。
