from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Finding:
    title: str
    description: str
    severity: Severity
    file: str | None = None
    line: int | None = None


@dataclass
class PluginResult:
    plugin_name: str
    score: float  # 0-100, higher = more risk
    passed: bool
    findings: list[Finding] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ReleaseContext:
    repo: str
    pr_number: int
    sha: str
    changed_files: list[str]
    pr_title: str
    pr_body: str
    clone_dir: str | None = None  # local checkout path for analysis


class BasePlugin(ABC):
    @abstractmethod
    async def evaluate(self, context: ReleaseContext) -> PluginResult:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
