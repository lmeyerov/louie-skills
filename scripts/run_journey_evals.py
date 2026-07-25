#!/usr/bin/env python3
"""Validate and score sanitized Louie skill journey responses.

This evaluator is offline: it reads JSON files, applies structural and regex
checks, and never calls a model or Louie service.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_DIMENSIONS = {
    "discovery",
    "text-query",
    "dataframe",
    "multi-turn",
    "implicit-cursor",
    "reasoning-final",
    "phases-progress",
    "mixed-partial-stream",
    "error-recovery",
    "sdk-rest-handoff",
    "contract-discovery",
    "authentication",
    "privacy-org",
    "backward-compatibility",
    "live-test-safety",
}
REQUIRED_PERSONAS = {
    "notebook-data-analyst",
    "security-investigator",
    "application-developer",
    "platform-operator",
}
VALID_SUPPORT = {"current", "product-gap"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"{path}: cannot read file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def validate_journey(journey: Any) -> list[str]:
    """Return deterministic schema and coverage errors."""
    errors: list[str] = []
    if not isinstance(journey, dict):
        return ["journey: expected an object"]

    for field in ("id", "description"):
        if not isinstance(journey.get(field), str) or not journey[field].strip():
            errors.append(f"journey.{field}: expected a non-empty string")

    coverage = journey.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("journey.coverage: expected an object")
        coverage = {}

    personas = coverage.get("personas")
    dimensions = coverage.get("dimensions")
    if not _string_list(personas) or len(set(personas)) < 4:
        errors.append("journey.coverage.personas: expected at least 4 unique strings")
        persona_set: set[str] = set()
    else:
        persona_set = set(personas)
        if len(persona_set) != len(personas):
            errors.append("journey.coverage.personas: duplicate persona")
        missing_personas = sorted(REQUIRED_PERSONAS - persona_set)
        if missing_personas:
            errors.append(
                "journey.coverage.personas: missing required personas: "
                + ", ".join(missing_personas)
            )

    if not _string_list(dimensions):
        errors.append("journey.coverage.dimensions: expected a non-empty string list")
        dimension_set: set[str] = set()
    else:
        dimension_set = set(dimensions)
        if len(dimension_set) != len(dimensions):
            errors.append("journey.coverage.dimensions: duplicate dimension")
        missing = sorted(REQUIRED_DIMENSIONS - dimension_set)
        if missing:
            errors.append(
                "journey.coverage.dimensions: missing required coverage: "
                + ", ".join(missing)
            )

    cases = journey.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("journey.cases: expected a non-empty list")
        return errors

    seen_ids: set[str] = set()
    exercised_personas: set[str] = set()
    exercised_dimensions: set[str] = set()
    support_seen: set[str] = set()

    for index, case in enumerate(cases):
        prefix = f"journey.cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix}: expected an object")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix}.id: expected a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{prefix}.id: duplicate case id {case_id!r}")
        else:
            seen_ids.add(case_id)

        for field in ("persona", "task", "prompt"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                errors.append(f"{prefix}.{field}: expected a non-empty string")
        if isinstance(case.get("persona"), str) and case["persona"] not in persona_set:
            errors.append(
                f"{prefix}.persona: {case['persona']!r} is absent from coverage.personas"
            )
        elif isinstance(case.get("persona"), str):
            exercised_personas.add(case["persona"])

        support = case.get("support")
        if support not in VALID_SUPPORT:
            errors.append(
                f"{prefix}.support: expected one of {sorted(VALID_SUPPORT)}, "
                f"got {support!r}"
            )
        else:
            support_seen.add(support)

        case_dimensions = case.get("dimensions")
        if not _string_list(case_dimensions):
            errors.append(f"{prefix}.dimensions: expected a non-empty string list")
        else:
            if len(set(case_dimensions)) != len(case_dimensions):
                errors.append(f"{prefix}.dimensions: duplicate dimension")
            for dimension in case_dimensions:
                if dimension not in dimension_set:
                    errors.append(
                        f"{prefix}.dimensions: unknown dimension {dimension!r}"
                    )
                exercised_dimensions.add(dimension)

        checks = case.get("checks")
        if not isinstance(checks, dict):
            errors.append(f"{prefix}.checks: expected an object")
            continue

        positive_patterns = checks.get("regex")
        if not _string_list(positive_patterns):
            errors.append(f"{prefix}.checks.regex: expected a non-empty string list")
            positive_patterns = []

        negative_patterns = checks.get("must_not_regex", [])
        if not isinstance(negative_patterns, list) or not all(
            isinstance(item, str) and item for item in negative_patterns
        ):
            errors.append(
                f"{prefix}.checks.must_not_regex: expected a string list"
            )
            negative_patterns = []

        max_lines = checks.get("max_lines")
        if not isinstance(max_lines, int) or isinstance(max_lines, bool) or max_lines < 1:
            errors.append(f"{prefix}.checks.max_lines: expected an integer >= 1")

        for kind, patterns in (
            ("regex", positive_patterns),
            ("must_not_regex", negative_patterns),
        ):
            for pattern_index, pattern in enumerate(patterns):
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(
                        f"{prefix}.checks.{kind}[{pattern_index}]: "
                        f"invalid regex {pattern!r}: {exc}"
                    )

    unexercised_personas = sorted(REQUIRED_PERSONAS - exercised_personas)
    if unexercised_personas:
        errors.append(
            "journey.cases: required personas not exercised: "
            + ", ".join(unexercised_personas)
        )
    unexercised = sorted(REQUIRED_DIMENSIONS - exercised_dimensions)
    if unexercised:
        errors.append(
            "journey.cases: required dimensions not exercised: "
            + ", ".join(unexercised)
        )
    if support_seen != VALID_SUPPORT:
        errors.append(
            "journey.cases: suite must include both current and product-gap cases"
        )
    return errors


def validate_responses(journey: dict[str, Any], responses: Any) -> list[str]:
    if not isinstance(responses, dict):
        return ["responses: expected an object mapping case IDs to strings"]
    errors: list[str] = []
    case_ids = {case["id"] for case in journey["cases"]}
    extra = sorted(set(responses) - case_ids)
    if extra:
        errors.append("responses: unknown case IDs: " + ", ".join(extra))
    for case_id, answer in responses.items():
        if not isinstance(case_id, str) or not isinstance(answer, str):
            errors.append(f"responses.{case_id}: expected a string answer")
    return errors


def check_answer(case: dict[str, Any], answer: str) -> list[str]:
    checks = case["checks"]
    failures: list[str] = []
    for pattern in checks["regex"]:
        if not re.search(pattern, answer, re.IGNORECASE | re.MULTILINE):
            failures.append(f"missing /{pattern}/")
    for pattern in checks.get("must_not_regex", []):
        if re.search(pattern, answer, re.IGNORECASE | re.MULTILINE):
            failures.append(f"forbidden /{pattern}/")
    actual_lines = len(answer.splitlines())
    if actual_lines > checks["max_lines"]:
        failures.append(
            f"line limit exceeded: {actual_lines} > {checks['max_lines']}"
        )
    return failures


def evaluate(
    journey: dict[str, Any], responses: dict[str, str]
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in journey["cases"]:
        case_id = case["id"]
        failures = (
            ["missing response"]
            if case_id not in responses
            else check_answer(case, responses[case_id])
        )
        results.append(
            {
                "id": case_id,
                "persona": case["persona"],
                "support": case["support"],
                "passed": not failures,
                "failures": failures,
            }
        )

    passed = sum(result["passed"] for result in results)
    total = len(results)
    return {
        "journey_id": journey["id"],
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "pass_rate": passed / total if total else 0.0,
        "results": results,
    }


def _write_metrics(path: Path, report: dict[str, Any]) -> None:
    aggregate = {key: value for key, value in report.items() if key != "results"}
    aggregate["failed_case_ids"] = [
        result["id"] for result in report["results"] if not result["passed"]
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journey", type=Path)
    parser.add_argument("responses", type=Path, nargs="?")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--json-output",
        type=Path,
        help="write sanitized aggregate metrics without response text",
    )
    args = parser.parse_args(argv)

    try:
        journey = load_json(args.journey)
    except ValueError as exc:
        print(f"SCHEMA ERROR: {exc}", file=sys.stderr)
        return 2
    schema_errors = validate_journey(journey)
    if schema_errors:
        for error in schema_errors:
            print(f"SCHEMA ERROR: {error}", file=sys.stderr)
        return 2

    if args.validate_only:
        print(
            f"validated {journey['id']}: {len(journey['cases'])} cases, "
            f"{len(journey['coverage']['personas'])} personas"
        )
        return 0
    if args.responses is None:
        parser.error("responses is required unless --validate-only is used")

    try:
        responses = load_json(args.responses)
    except ValueError as exc:
        print(f"RESPONSE ERROR: {exc}", file=sys.stderr)
        return 2
    response_errors = validate_responses(journey, responses)
    if response_errors:
        for error in response_errors:
            print(f"RESPONSE ERROR: {error}", file=sys.stderr)
        return 2

    report = evaluate(journey, responses)
    for result in report["results"]:
        if result["passed"]:
            print(f"PASS {result['id']}")
        else:
            print(f"FAIL {result['id']}: {'; '.join(result['failures'])}")
    print(
        f"{report['passed']}/{report['total']} journeys passed "
        f"({report['pass_rate']:.1%})"
    )
    if args.json_output is not None:
        _write_metrics(args.json_output, report)
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
