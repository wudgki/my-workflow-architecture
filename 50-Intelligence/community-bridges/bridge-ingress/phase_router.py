"""Phase routing using 50-Intelligence/pipelines/keywords.yaml.

Loads the YAML on construction. Each call to reload_if_changed() re-stats
the file and reloads only if the mtime moved. There is no background
thread; the webhook handler invokes reload_if_changed() once per request,
which means at most one stat() per request and a re-read only when the
operator actually edits the file. This is the simpler hot-reload model
agreed for PR #15 (vs. the periodic background poller hinted at in the
SPEC).

Matching rules (per SPEC-bridge-ingress.md sec. 4.1):
  - Case-insensitive substring match on lower-cased text.
  - Iterate phase_1 .. phase_4 in order. Within each phase, if any
    `exclude` term is present in the text, skip that phase. Otherwise
    if any `include` term hits, return that phase number.
  - If any `global_exclude` term hits, force phase=None regardless.
  - No match anywhere => phase=None (caller routes to To-Process).
  - Return value is a string: "phase_1" .. "phase_4" or None.

ASCII-only.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class _PhaseSpec:
    number: int
    label: str
    include: list[str]
    exclude: list[str]


class PhaseRouter:
    def __init__(self, keywords_path: str) -> None:
        self._path = keywords_path
        self._mtime: float = 0.0
        self._phases: list[_PhaseSpec] = []
        self._global_exclude: list[str] = []
        self._loaded: bool = False
        self._load()

    @property
    def loaded(self) -> bool:
        return self._loaded

    def _load(self) -> None:
        try:
            stat_result = os.stat(self._path)
        except FileNotFoundError:
            self._mtime = 0.0
            self._phases = []
            self._global_exclude = []
            self._loaded = False
            return
        with open(self._path, "rb") as fh:
            data = yaml.safe_load(fh) or {}
        phases: list[_PhaseSpec] = []
        for n in (1, 2, 3, 4):
            block = data.get("phase_" + str(n)) or {}
            include_raw = block.get("include") or []
            exclude_raw = block.get("exclude") or []
            include = [str(x).lower() for x in include_raw]
            exclude = [str(x).lower() for x in exclude_raw]
            label = str(block.get("label") or ("phase_" + str(n)))
            phases.append(
                _PhaseSpec(
                    number=n,
                    label=label,
                    include=include,
                    exclude=exclude,
                )
            )
        self._phases = phases
        self._global_exclude = [
            str(x).lower() for x in (data.get("global_exclude") or [])
        ]
        self._mtime = stat_result.st_mtime
        self._loaded = True

    def reload_if_changed(self) -> bool:
        """Re-stat the keywords file; reload if mtime moved.

        Returns True if a reload happened, False otherwise. Safe to call
        from any thread (single-threaded Python webhook handler in v1).
        """
        try:
            current = os.stat(self._path).st_mtime
        except FileNotFoundError:
            if self._loaded:
                self._mtime = 0.0
                self._phases = []
                self._global_exclude = []
                self._loaded = False
                return True
            return False
        if current != self._mtime:
            self._load()
            return True
        return False

    def route(self, text: str) -> Optional[str]:
        """Return 'phase_1'..'phase_4' matching `text`, or None for no match."""
        if not text:
            return None
        haystack = text.lower()
        if any(term and term in haystack for term in self._global_exclude):
            return None
        for phase in self._phases:
            if any(term and term in haystack for term in phase.exclude):
                continue
            if any(term and term in haystack for term in phase.include):
                return "phase_" + str(phase.number)
        return None
