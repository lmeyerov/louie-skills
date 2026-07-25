from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_journey_evals.py"
JOURNEY = ROOT / "evals" / "journeys" / "louie_api_v1.json"
GOLDEN = ROOT / "evals" / "fixtures" / "louie_api_v1_golden.json"

SPEC = importlib.util.spec_from_file_location("run_journey_evals", SCRIPT)
assert SPEC and SPEC.loader
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


class JourneySchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.journey = json.loads(JOURNEY.read_text(encoding="utf-8"))

    def test_repository_journey_is_valid(self) -> None:
        self.assertEqual(EVAL.validate_journey(self.journey), [])

    def test_duplicate_case_id_is_rejected(self) -> None:
        journey = copy.deepcopy(self.journey)
        journey["cases"][1]["id"] = journey["cases"][0]["id"]
        errors = EVAL.validate_journey(journey)
        self.assertTrue(any("duplicate case id" in error for error in errors))

    def test_malformed_regex_is_rejected(self) -> None:
        journey = copy.deepcopy(self.journey)
        journey["cases"][0]["checks"]["regex"] = ["["]
        errors = EVAL.validate_journey(journey)
        self.assertTrue(any("invalid regex" in error for error in errors))

    def test_missing_required_dimension_is_rejected(self) -> None:
        journey = copy.deepcopy(self.journey)
        journey["coverage"]["dimensions"].remove("reasoning-final")
        errors = EVAL.validate_journey(journey)
        self.assertTrue(any("reasoning-final" in error for error in errors))

    def test_missing_required_persona_is_rejected(self) -> None:
        journey = copy.deepcopy(self.journey)
        journey["coverage"]["personas"].remove("platform-operator")
        errors = EVAL.validate_journey(journey)
        self.assertTrue(any("platform-operator" in error for error in errors))

    def test_unexercised_required_persona_is_rejected(self) -> None:
        journey = copy.deepcopy(self.journey)
        for case in journey["cases"]:
            if case["persona"] == "platform-operator":
                case["persona"] = "application-developer"
        errors = EVAL.validate_journey(journey)
        self.assertTrue(
            any("required personas not exercised" in error for error in errors)
        )

    def test_duplicate_case_dimension_is_rejected(self) -> None:
        journey = copy.deepcopy(self.journey)
        journey["cases"][0]["dimensions"].append(
            journey["cases"][0]["dimensions"][0]
        )
        errors = EVAL.validate_journey(journey)
        self.assertTrue(any("duplicate dimension" in error for error in errors))

    def test_invalid_max_lines_bool_is_rejected(self) -> None:
        journey = copy.deepcopy(self.journey)
        journey["cases"][0]["checks"]["max_lines"] = True
        errors = EVAL.validate_journey(journey)
        self.assertTrue(any("max_lines" in error for error in errors))

    def test_unknown_response_id_is_rejected(self) -> None:
        responses = {"unknown": "answer"}
        errors = EVAL.validate_responses(self.journey, responses)
        self.assertEqual(errors, ["responses: unknown case IDs: unknown"])

    def test_non_string_response_is_rejected(self) -> None:
        errors = EVAL.validate_responses(
            self.journey, {self.journey["cases"][0]["id"]: ["not", "text"]}
        )
        self.assertTrue(any("expected a string answer" in error for error in errors))


class JourneyEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.journey = json.loads(JOURNEY.read_text(encoding="utf-8"))
        self.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_golden_fixture_passes_every_case(self) -> None:
        report = EVAL.evaluate(self.journey, self.golden)
        self.assertEqual(report["passed"], report["total"])
        self.assertEqual(report["failed"], 0)

    def test_missing_response_fails_with_case_diagnostic(self) -> None:
        responses = dict(self.golden)
        removed = self.journey["cases"][0]["id"]
        responses.pop(removed)
        report = EVAL.evaluate(self.journey, responses)
        result = next(item for item in report["results"] if item["id"] == removed)
        self.assertEqual(result["failures"], ["missing response"])

    def test_forbidden_pattern_and_line_limit_fail(self) -> None:
        case = copy.deepcopy(self.journey["cases"][0])
        case["checks"]["max_lines"] = 1
        failures = EVAL.check_answer(
            case,
            "from louieai import louie\n"
            "lui = louie(share_mode='Private')\n"
            "lui('x')\n"
            "print(lui.text)\n"
            "share_mode='Public'",
        )
        self.assertTrue(any("forbidden" in failure for failure in failures))
        self.assertTrue(any("line limit" in failure for failure in failures))

    def test_positional_text_selection_claim_is_rejected(self) -> None:
        """Cursor.text follows the server final-answer pointer, not position."""
        case = next(
            item
            for item in self.journey["cases"]
            if item["id"] == "developer_text_selection_semantics"
        )
        answer = (
            "- Cursor.text selects the first text element.\n"
            "- A history proxy selects the first text element.\n"
            "- Response.text selects the first text element."
        )
        failures = EVAL.check_answer(case, answer)
        self.assertTrue(any("forbidden" in failure for failure in failures))

    def test_denying_the_reasoning_accessor_is_rejected(self) -> None:
        """Reasoning is readable back; an answer denying it must not pass."""
        case = next(
            item
            for item in self.journey["cases"]
            if item["id"] == "investigator_reasoning_surface"
        )
        answer = (
            "Set lui.traces = True for live display. The cursor does not retain "
            "any reasoning afterward."
        )
        self.assertTrue(EVAL.check_answer(case, answer))

    def test_top_level_parent_field_claim_is_rejected(self) -> None:
        """Run hierarchy is run_node.parent_id, verified against the live stream."""
        case = next(
            item
            for item in self.journey["cases"]
            if item["id"] == "operator_phases_progress"
        )
        answer = (
            "Use lui.run_updates and lui.phases. Each run_node has a parent field "
            "and children, and repeat records upsert by id. parent_id is unused."
        )
        failures = EVAL.check_answer(case, answer)
        self.assertTrue(any("forbidden" in failure for failure in failures))

    def test_graphistry_server_does_not_satisfy_legacy_server_check(self) -> None:
        case = next(
            item
            for item in self.journey["cases"]
            if item["id"] == "developer_auth_configuration"
        )
        answer = (
            "Use GRAPHISTRY_PERSONAL_KEY_ID and GRAPHISTRY_PERSONAL_KEY_SECRET "
            "with graphistry_server= and server_url=. The client is rejected "
            "when configuration is legacy."
        )
        failures = EVAL.check_answer(case, answer)
        self.assertTrue(
            any("(?:^|[^_])server=" in failure for failure in failures)
        )

    def test_metrics_writer_excludes_response_text_and_case_details(self) -> None:
        report = EVAL.evaluate(self.journey, self.golden)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.json"
            EVAL._write_metrics(path, report)
            metrics = json.loads(path.read_text(encoding="utf-8"))
        self.assertNotIn("results", metrics)
        self.assertEqual(metrics["failed_case_ids"], [])
        self.assertEqual(metrics["pass_rate"], 1.0)

    def test_cli_returns_one_for_a_failed_answer(self) -> None:
        responses = dict(self.golden)
        responses[self.journey["cases"][0]["id"]] = "unsupported answer"
        with tempfile.TemporaryDirectory() as directory:
            response_path = Path(directory) / "responses.json"
            response_path.write_text(json.dumps(responses), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(SCRIPT), str(JOURNEY), str(response_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(process.returncode, 1)
        self.assertIn("FAIL notebook_onboarding_text", process.stdout)

    def test_cli_returns_two_for_malformed_journey_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            journey_path = Path(directory) / "journey.json"
            journey_path.write_text("{", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(SCRIPT), str(journey_path), "--validate-only"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(process.returncode, 2)
        self.assertIn("SCHEMA ERROR", process.stderr)


if __name__ == "__main__":
    unittest.main()
