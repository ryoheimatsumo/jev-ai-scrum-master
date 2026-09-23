"""Versioned task contracts; extra fields cannot smuggle approvals or PASS flags."""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, field_validator, model_validator

from .common import relative_path

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Status(StrEnum):
    PLANNING = "PLANNING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFYING = "VERIFYING"
    NEEDS_FIX = "NEEDS_FIX"
    WAITING_USER = "WAITING_USER"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class Criterion(Model):
    id: Identifier
    given: Text
    when: Text
    then: Text
    method: Literal["test", "process", "manual"] = "test"
    check_ids: list[Identifier] = Field(default_factory=list, max_length=30)
    # Exact test identity, not just a total count: {"unit": ["module.Class::test_name"]}.
    case_ids: dict[str, list[str]] = Field(default_factory=dict)
    manual_instructions: str | None = None

    @model_validator(mode="after")
    def verification_is_explicit(self):
        if len(self.check_ids) != len(set(self.check_ids)):
            raise ValueError("Duplicate check ids")
        if self.method == "manual":
            if self.check_ids or self.case_ids or not (self.manual_instructions or "").strip():
                raise ValueError("Manual criteria require instructions and no automatic checks")
        elif not self.check_ids:
            raise ValueError("An automatic criterion requires a check_id")
        if self.method == "test":
            if set(self.case_ids) != set(self.check_ids):
                raise ValueError("Map every behavioral check to explicit required test case ids")
            if any(not ids or any(not x.strip() for x in ids) for ids in self.case_ids.values()):
                raise ValueError("Required test case ids cannot be empty")
        return self


class Contract(Model):
    title: Text
    kind: Literal["feature", "bug", "refactor", "test", "docs", "spike"] = "feature"
    goal: Text
    in_scope: list[Text] = Field(min_length=1, max_length=30)
    out_of_scope: list[Text] = Field(default_factory=list, max_length=30)
    criteria: list[Criterion] = Field(min_length=1, max_length=30)
    review_profile: Literal["light", "standard", "strict"] = "standard"
    blockers: list[Text] = Field(default_factory=list)
    dependencies: list[Identifier] = Field(default_factory=list)
    parent_id: Identifier | None = None
    source_refs: list[str] = Field(default_factory=list, max_length=30)
    # Values here cannot override project policy; smaller limits can be added later.

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [c.id for c in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("Criterion ids must be unique")
        if self.review_profile == "light" and self.kind != "docs":
            raise ValueError("Light is restricted to approved documentation-only changes")
        if self.review_profile == "light" and any(c.method != "process" for c in self.criteria):
            raise ValueError("Light criteria must be deterministic process checks")
        for path in self.source_refs:
            relative_path(path)
        return self


class Check(Model):
    argv: list[Text] = Field(min_length=1, max_length=100)
    cwd: str = "."
    kind: Literal["test", "process"] = "test"
    parser: Literal["junit", "json", "exit"] = "junit"
    report_path: str | None = None
    timeout_seconds: float = Field(default=600, ge=0.05, le=3600)
    min_tests: int = Field(default=1, ge=1)
    output_limit_bytes: int = Field(default=262144, ge=1024, le=4194304)

    @model_validator(mode="after")
    def valid_report(self):
        relative_path(self.cwd)
        if self.kind == "test" and self.parser == "exit":
            raise ValueError("Exit status alone cannot verify behavior")
        if self.parser != "exit":
            if not self.report_path:
                raise ValueError("A fresh structured report is required")
            relative_path(self.report_path)
            if not self.report_path.startswith(".jev-sm-output/"):
                raise ValueError("Reports must be written below .jev-sm-output/")
        elif self.report_path:
            raise ValueError("Exit-only checks do not consume a report")
        for arg in self.argv:
            if "\x00" in arg:
                raise ValueError("NUL in command argument")
        return self


class Settings(Model):
    schema_version: Literal[1] = 1
    checks: dict[Identifier, Check] = Field(default_factory=dict)
    dod_check_ids: list[Identifier] = Field(default_factory=list)
    protected_globs: list[str] = Field(default_factory=lambda: [
        "tests/*", "**/test_*.py", "test_*.py", "*.test.*", "*.spec.*",
        ".github/*", ".jev-sm/*", "pyproject.toml", "package.json",
    ])
    strict_globs: list[str] = Field(default_factory=lambda: [
        "auth*", "payment*", "billing*", "**/auth*", "**/payment*", "**/billing*", "migrations/*",
    ])
    # These input exclusions are shown on approval. No arbitrary pattern-based exclusions.
    excluded_directories: list[str] = Field(default_factory=lambda: [
        ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    ])
    max_snapshot_files: int = Field(default=20000, ge=1, le=200000)
    max_snapshot_bytes: int = Field(default=104857600, ge=1024)
    max_verification_rounds: int = Field(default=4, ge=1, le=20)
    max_unchanged_failures: int = Field(default=3, ge=1, le=10)
    jev_enabled: bool = False
    jev_model: str = "jev-1.13.0"
    jev_max_payload_chars: int = Field(default=24000, ge=1000, le=100000)
    jev_max_calls_per_task: int = Field(default=100, ge=1, le=5000)
    # Cache is advisory only, local to the workspace/task, and stores no raw input.
    jev_cache_ttl_seconds: int = Field(default=86400, ge=0, le=604800)
    jev_cache_max_entries: int = Field(default=512, ge=0, le=10000)

    @field_validator("excluded_directories")
    @classmethod
    def fixed_directory_names(cls, values):
        allowed = {".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
        if set(values) - allowed:
            raise ValueError("Only documented generated/dependency directories can be excluded")
        return values

    @model_validator(mode="after")
    def dod_exists(self):
        if set(self.dod_check_ids) - set(self.checks):
            raise ValueError("Unknown DoD check")
        return self


class Case(Model):
    id: Text
    status: Literal["passed", "failed", "skipped"]


class TestReport(Model):
    schema_version: Literal[1] = 1
    cases: list[Case] = Field(default_factory=list, max_length=100000)

    @model_validator(mode="after")
    def no_duplicates(self):
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Test case identities must be unique")
        return self


class Improvement(Model):
    title: Text
    hypothesis: Text
    proposed_action: Text
    task_kinds: list[str] = Field(min_length=1)
    path_globs: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    positive_example: Text
    negative_example: Text
    action_kind: Literal["planning_hint", "verification_candidate"]


class ContextSnippet(Model):
    id: Identifier
    text: Annotated[str, StringConstraints(max_length=100000)]
    mandatory: StrictBool = False


class ContextRequest(Model):
    query: Text
    snippets: list[ContextSnippet] = Field(min_length=1, max_length=30)
    max_chars: int = Field(default=8000, ge=1, le=100000, strict=True)

    @model_validator(mode="after")
    def unique_snippets(self):
        if len({s.id for s in self.snippets}) != len(self.snippets):
            raise ValueError("Snippet ids must be unique")
        return self
