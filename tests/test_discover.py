"""Discovery contract checks; model calls are replaced with a local fake."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.teacher_profile import discover


DETAILED = "### G-T1: 선택 이유\nTiming and extent: 짧은 언급\n### U-C1: 전환 후보\nConfidence: Low"
RUNTIME = "### G-T1: 선택 이유\n- 설명 조절: 실행 중 짧은 언급\n### U-C1: 전환 후보\n- 상태: 후보\n- 적용 조건: 기존 접근의 한계 확인 후"
RESPONSE = f"<detailed_policy>\n{DETAILED}\n</detailed_policy>\n<runtime_policy>\n{RUNTIME}\n</runtime_policy>"


class PolicyOutputTests(unittest.TestCase):
    def test_split_preserves_both_documents(self):
        self.assertEqual(discover.split_policy_output(RESPONSE, len(RUNTIME)), (DETAILED, RUNTIME))

    def test_rejects_over_budget_without_truncation(self):
        with self.assertRaisesRegex(ValueError, "초과"):
            discover.split_policy_output(RESPONSE, len(RUNTIME) - 1)

    def test_rejects_missing_and_duplicate_ids(self):
        for runtime in (RUNTIME.replace("### U-C1:", "### U-C2:"), RUNTIME + "\n### G-T1: 중복"):
            result = f"<detailed_policy>{DETAILED}</detailed_policy><runtime_policy>{runtime}</runtime_policy>"
            with self.subTest(runtime=runtime), self.assertRaisesRegex(ValueError, "ID"):
                discover.split_policy_output(result, 12000)

    def test_checks_ids_emitted_outside_original_naming_convention(self):
        for policy_id in ("SEQ-1", "UC-P1", "UC-T2"):
            detailed = DETAILED + f"\n### {policy_id}: additional policy"
            result = f"<detailed_policy>{detailed}</detailed_policy><runtime_policy>{RUNTIME}</runtime_policy>"
            with self.subTest(policy_id=policy_id), self.assertRaisesRegex(ValueError, "ID"):
                discover.split_policy_output(result, 12000)

    def test_rejects_partial_and_uncompressible_response(self):
        for result in (RESPONSE.replace("</runtime_policy>", ""),
                       f"<detailed_policy>{DETAILED}</detailed_policy><runtime_policy>COMPRESSION_BUDGET_EXCEEDED</runtime_policy>"):
            with self.subTest(result=result), self.assertRaises(ValueError):
                discover.split_policy_output(result, 12000)

    def test_second_file_conflict_preserves_old_output_and_cleans_new_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "policy.md"
            output.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                discover.save_policy_outputs(output, DETAILED, RUNTIME)
            self.assertEqual(output.read_text(), "existing")
            self.assertFalse(output.with_name("policy_detailed.md").exists())


class DiscoveryFlowTests(unittest.TestCase):
    def run_main(self, root, response=RESPONSE, budget=12000, verdict="지지됨"):
        def model_response(**kwargs):
            if not getattr(kwargs.get("config"), "response_schema", None):
                return SimpleNamespace(text=response)
            payload = json.loads(kwargs["contents"][1])
            result = {"assessments": [{"claim_id": c["id"], "verdict": verdict(c) if callable(verdict) else verdict,
                       "reason": "test evidence", "evidence": [{"problem_id": "003", "step_ids": [],
                       "quote": "짧은 설명 / 관련 행동 전 / 짧은 언급 / 비관찰"}]} for c in payload["claims"]],
                       "coverage_findings": []}
            return SimpleNamespace(text=json.dumps(result, ensure_ascii=False))
        model = Mock()
        model.generate_content.side_effect = model_response
        client = SimpleNamespace(models=model)
        argv = ["discover", "--max-runtime-chars", str(budget)]
        with patch.object(discover, "ROOT", root), patch.object(discover, "get_client", return_value=client), \
                patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()):
            discover.main()
        return model

    def prepare_input(self, root):
        directory = root / "data/teacher_profile/analysis/v4"
        directory.mkdir(parents=True)
        (directory / "003.txt").write_text("짧은 설명 / 관련 행동 전 / 짧은 언급 / 비관찰", encoding="utf-8")
        old = root / "data/teacher_profile/profiles/teacher_policy_v4.md"
        old.write_text("existing-v4", encoding="utf-8")
        return old

    def test_new_outputs_and_source_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = self.prepare_input(root)
            model = self.run_main(root)
            self.assertEqual(old.read_text(), "existing-v4")
            self.assertEqual((root / "data/teacher_profile/profiles/teacher_policy_v5.md").read_text().strip(), RUNTIME)
            self.assertEqual((root / "data/teacher_profile/profiles/teacher_policy_v5_detailed.md").read_text().strip(), DETAILED)
            run = next((root / "data/teacher_profile/runs/discovery").iterdir())
            self.assertEqual((run / "raw_response.txt").read_text(), RESPONSE)
            self.assertEqual((run / "discovery_prompt.txt").read_text(),
                             discover.build_discovery_prompt(12000))
            self.assertIn("짧은 언급", (run / "analysis_input.txt").read_text())
            settings = json.loads((run / "settings.json").read_text())
            self.assertEqual(settings["max_runtime_chars"], 12000)
            self.assertEqual(model.generate_content.call_count, 2)
            prompt, analysis = model.generate_content.call_args_list[0].kwargs["contents"]
            self.assertIn("12000", prompt)
            self.assertNotIn("__MAX_RUNTIME_CHARS__", prompt)
            self.assertIn("비관찰", analysis)

    def test_invalid_response_kept_without_publishing_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_input(root)
            with self.assertRaisesRegex(ValueError, "원본 응답"):
                self.run_main(root, budget=1)
            self.assertFalse((root / "data/teacher_profile/profiles/teacher_policy_v5.md").exists())
            self.assertFalse((root / "data/teacher_profile/profiles/teacher_policy_v5_detailed.md").exists())
            raw = next((root / "data/teacher_profile/runs/discovery").glob("*/raw_response.txt"))
            self.assertEqual(raw.read_text(), RESPONSE)

    def test_semantic_issue_blocks_publish_and_keeps_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_input(root)
            with self.assertRaisesRegex(SystemExit, "보류"):
                self.run_main(root, verdict="부분 지지")
            self.assertFalse((root / "data/teacher_profile/profiles/teacher_policy_v5.md").exists())
            run = next((root / "data/teacher_profile/runs/discovery").iterdir())
            self.assertTrue((run / "draft_runtime.md").is_file())
            review = json.loads((run / "validation.json").read_text())
            self.assertFalse(review["passed"])
            self.assertIn("부분 지지", (run / "validation.md").read_text())

    def test_mixed_review_publishes_only_supported_complete_rules(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_input(root)
            self.run_main(root, verdict=lambda c: '부분 지지' if c['policy_id'] == 'U-C1' else '지지됨')
            runtime = (root / 'data/teacher_profile/profiles/teacher_policy_v5.md').read_text()
            detail = (root / 'data/teacher_profile/profiles/teacher_policy_v5_detailed.md').read_text()
            for text in (runtime, detail):
                self.assertIn('G-T1', text)
                self.assertNotIn('U-C1', text)
            run = next((root / 'data/teacher_profile/runs/discovery').iterdir())
            selection = json.loads((run / 'selection.json').read_text())
            self.assertTrue(selection['publishable'])
            self.assertTrue(selection['limited'])
            self.assertIn('U-C1', (run / 'draft_runtime.md').read_text())

    def test_existing_policy_can_be_reviewed_without_extraction_or_rewriting(self):
        from src.teacher_profile.policy_validation import build_claims
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_input(root)
            output = root / "data/existing.md"
            detail = root / "data/existing_detailed.md"
            output.write_text(RUNTIME)
            detail.write_text(DETAILED)
            assessments = [{"claim_id": c["id"], "verdict": "지지됨", "reason": "test",
                            "evidence": [{"problem_id": "003", "step_ids": [],
                            "quote": "짧은 설명 / 관련 행동 전 / 짧은 언급 / 비관찰"}]}
                           for c in build_claims(DETAILED, RUNTIME)]
            model = Mock()
            model.generate_content.return_value = SimpleNamespace(text=json.dumps({
                "assessments": assessments, "coverage_findings": []}, ensure_ascii=False))
            with patch.object(discover, "ROOT", root), \
                    patch.object(discover, "get_client", return_value=SimpleNamespace(models=model)), \
                    patch.object(discover, "discover_policy") as extraction, \
                    patch("sys.argv", ["discover", "--verify-existing", "data/existing.md"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                discover.main()
            extraction.assert_not_called()
            self.assertEqual(model.generate_content.call_count, 1)
            self.assertEqual(output.read_text(), RUNTIME)
            self.assertEqual(detail.read_text(), DETAILED)

    def test_validation_request_failure_keeps_drafts_and_blocks_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_input(root)
            with patch.object(discover, "review_policy", side_effect=RuntimeError("model unavailable")):
                with self.assertRaisesRegex(RuntimeError, "근거 검증 실패"):
                    self.run_main(root)
            self.assertFalse((root / "data/teacher_profile/profiles/teacher_policy_v5.md").exists())
            run = next((root / "data/teacher_profile/runs/discovery").iterdir())
            self.assertTrue((run / "draft_runtime.md").is_file())
            self.assertIn("model unavailable", (run / "validation_error.txt").read_text())

    def test_existing_output_rejected_before_model_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_input(root)
            output = root / "data/teacher_profile/profiles/teacher_policy_v5.md"
            output.write_text("existing-v5", encoding="utf-8")
            with patch.object(discover, "ROOT", root), patch.object(discover, "get_client") as get_client, \
                    patch("sys.argv", ["discover"]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    discover.main()
                get_client.assert_not_called()
            self.assertEqual(output.read_text(), "existing-v5")


if __name__ == "__main__":
    unittest.main()
