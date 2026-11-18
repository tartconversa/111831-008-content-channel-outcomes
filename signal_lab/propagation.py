"""传播路径追踪：把观察记录分为传播路径、独立响应与起点缺失三类。

路径只描述扩散结构（哪条记录下游于哪条、涉及哪些渠道），不跨记录累加数值：
同一内容在不同账号间的转发属于同一条路径，独立响应单独计数。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PropagationPath:
    """一条传播路径：同一内容从首条记录到下游转发的一组观察。"""

    root_id: str
    content_id: str | None
    relation: str  # 路径起点记录的 relation（origin 或 response）
    observation_ids: tuple[str, ...]
    source_ids: tuple[str, ...]

    @property
    def is_response(self):
        return self.relation == "response"

    @property
    def size(self):
        return len(self.observation_ids)


@dataclass(frozen=True)
class PropagationSummary:
    """同一内容（content_id）下的传播结构。"""

    content_id: str | None
    paths: tuple[PropagationPath, ...]  # 以 origin 起点的传播路径
    responses: tuple[PropagationPath, ...]  # 独立响应（relation=response）
    dangling: tuple[str, ...]  # path_root 指向缺失记录的观察 id

    @property
    def path_count(self):
        return len(self.paths)

    @property
    def response_count(self):
        return len(self.responses)

    @property
    def involved_sources(self):
        sources = set()
        for path in self.paths + self.responses:
            sources.update(path.source_ids)
        return tuple(sorted(sources))


def _resolve_root(start, by_id):
    """沿 path_root 追到路径起点；追不到（起点缺失、成环或未指明）返回 None。"""
    current = start
    seen = {start.observation_id}
    while current.relation == "reshare" and current.path_root is not None:
        nxt = by_id.get(current.path_root)
        if nxt is None or nxt.observation_id in seen:
            return None
        seen.add(nxt.observation_id)
        current = nxt
    if current.relation == "reshare":
        return None
    return current.observation_id


def build_paths(observations):
    """返回 (paths, dangling)。

    paths：按路径起点分组的 PropagationPath 元组（含独立响应，
    可用 path.is_response 区分）；dangling：path_root 无法解析到
    起点的观察记录（数据缺失，不计入任何路径）。
    """
    observations = tuple(observations)
    by_id = {obs.observation_id: obs for obs in observations}
    groups = {}
    dangling = []
    for obs in observations:
        if obs.relation == "reshare":
            root = _resolve_root(obs, by_id)
            if root is None:
                dangling.append(obs)
                continue
        else:
            root = obs.observation_id
        groups.setdefault(root, []).append(obs)

    paths = []
    for root_id in sorted(groups):
        members = sorted(
            groups[root_id], key=lambda obs: (obs.observed_on, obs.observation_id)
        )
        root_obs = by_id[root_id]
        paths.append(
            PropagationPath(
                root_id=root_id,
                content_id=root_obs.content_id,
                relation=root_obs.relation,
                observation_ids=tuple(obs.observation_id for obs in members),
                source_ids=tuple(sorted({obs.source_id for obs in members})),
            )
        )
    return tuple(paths), tuple(dangling)


def summarize_propagation(observations):
    """按 content_id 汇总传播结构：路径、独立响应与起点缺失记录。"""
    paths, dangling = build_paths(observations)
    content_ids = {path.content_id for path in paths}
    content_ids.update(obs.content_id for obs in dangling)
    summaries = []
    for content_id in sorted(content_ids, key=lambda c: (c is None, c or "")):
        own = tuple(path for path in paths if path.content_id == content_id)
        summaries.append(
            PropagationSummary(
                content_id=content_id,
                paths=tuple(path for path in own if not path.is_response),
                responses=tuple(path for path in own if path.is_response),
                dangling=tuple(
                    obs.observation_id
                    for obs in dangling
                    if obs.content_id == content_id
                ),
            )
        )
    return tuple(summaries)
