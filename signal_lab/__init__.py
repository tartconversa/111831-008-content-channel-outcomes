"""面向研究复核的数据观察与分析。"""

from .analysis import (
    COMPARABLE,
    DEFINITION_CHANGED,
    METRIC_UNKNOWN,
    MISSING_IN_END,
    MISSING_IN_START,
    PeriodComparison,
    SliceComparison,
    compare_periods,
)
from .catalog import SourceCatalog
from .definitions import DefinitionRegistry
from .propagation import (
    PropagationPath,
    PropagationSummary,
    build_paths,
    summarize_propagation,
)
from .records import MetricDefinition, Observation, Source
from .report import AnalysisReport, Reading, create_report

__all__ = [
    "AnalysisReport",
    "COMPARABLE",
    "DEFINITION_CHANGED",
    "DefinitionRegistry",
    "METRIC_UNKNOWN",
    "MISSING_IN_END",
    "MISSING_IN_START",
    "MetricDefinition",
    "Observation",
    "PeriodComparison",
    "PropagationPath",
    "PropagationSummary",
    "Reading",
    "SliceComparison",
    "Source",
    "SourceCatalog",
    "build_paths",
    "compare_periods",
    "create_report",
    "summarize_propagation",
]
