import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from src.teacher_profile.policy_validation import (
    build_claims, source_index, validate_review, review_policy,
    recover_review, recover_saved_review, select_supported_policies,
)

SOURCE = """### [Policy Trace]
**Step S01**
행동 A와 선택 이유
**Step S02**
행동 B와 설명
### [교수 행동 점검표]
비관찰 기록
"""


class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '003.txt').write_text(SOURCE)
        self.sources = source_index(self.root)
        self.claims = [{"id": "runtime/G-T1/delivery"}]
        self.review = {"assessments": [{"claim_id": self.claims[0]["id"], "verdict": "지지됨",
                       "reason": "장면 근거", "evidence": [{"problem_id": "003", "step_ids": ["S01"],
                       "quote": "행동 A와 선택 이유"}]}], "coverage_findings": []}

    def test_valid_evidence(self):
        self.assertTrue(validate_review(self.review, self.claims, self.sources)["passed"])

    def test_all_claims_must_be_reviewed_once(self):
        for rows in ([], self.review['assessments'] * 2):
            review = copy.deepcopy(self.review)
            review['assessments'] = rows
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, '누락·중복'):
                validate_review(review, self.claims, self.sources)

    def test_unknown_problem_step_reversed_order_and_false_quote_rejected(self):
        for change in ({"problem_id": "999"}, {"step_ids": ["S99"]},
                       {"step_ids": ["S02", "S01"]}, {"quote": "없는 발화"},
                       {"step_ids": ["S02"], "quote": "행동 A와 선택 이유"}):
            review = copy.deepcopy(self.review)
            review['assessments'][0]['evidence'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_review(review, self.claims, self.sources)

    def test_supported_without_evidence_rejected(self):
        self.review['assessments'][0]['evidence'] = []
        with self.assertRaisesRegex(ValueError, '근거가 없습니다'):
            validate_review(self.review, self.claims, self.sources)

    def test_any_unresolved_verdict_blocks(self):
        for verdict in ('부분 지지', '근거 부족', '근거와 충돌'):
            review = copy.deepcopy(self.review)
            review['assessments'][0]['verdict'] = verdict
            with self.subTest(verdict=verdict):
                self.assertFalse(validate_review(review, self.claims, self.sources)['passed'])

    def test_global_coverage_issue_blocks(self):
        self.review['coverage_findings'] = [{"verdict": "근거 부족", "reason": "관찰 기능 누락", "evidence": []}]
        self.assertFalse(validate_review(self.review, self.claims, self.sources)['passed'])

    def test_claims_include_multiline_sequences_unknown_fields_and_preamble(self):
        text = '# Runtime\n운용 지침\n### R-PS1: 순서\n- 순서:\n  1. 행동 A\n  2. 행동 B\n- 새 필드: 검토 대상\n'
        claims = build_claims(text, text)
        self.assertEqual(len({c['id'] for c in claims}), len(claims))
        self.assertTrue(any('행동 A' in c['text'] and '행동 B' in c['text'] for c in claims))
        self.assertTrue(any('새 필드' in c['text'] for c in claims))
        self.assertTrue(any(c['category'] == 'principles' for c in claims))

    def test_extra_rows_quarantined_without_discarding_expected_reviews(self):
        self.review['assessments'].append(dict(self.review['assessments'][0], claim_id='unexpected'))
        review = recover_review(self.review, self.claims, self.sources)
        self.assertTrue(review['passed'])
        self.assertEqual(len(review['integrity']['extra_assessments']), 1)
        self.assertEqual(review['integrity']['valid_count'], 1)

    def test_bad_quotes_missing_and_duplicate_rows_are_unverified_not_passed(self):
        for mutation in ('badquote', 'missing', 'duplicate'):
            response = copy.deepcopy(self.review)
            if mutation == 'badquote':
                response['assessments'][0]['evidence'][0]['quote'] = 'fabricated'
            elif mutation == 'missing':
                response['assessments'] = []
            else:
                response['assessments'] *= 2
            with self.subTest(mutation=mutation):
                review = recover_review(response, self.claims, self.sources)
                self.assertFalse(review['passed'])
                self.assertEqual(review['integrity']['unverified_count'], 1)
                self.assertEqual(review['assessments'][0]['verdict'], '근거 부족')

    def test_reference_evidence_is_loaded_from_source_not_model_text(self):
        row = self.review['assessments'][0]
        del row['evidence']
        row['evidence_refs'] = ['003/S01']
        review = recover_review(self.review, self.claims, self.sources)
        self.assertTrue(review['passed'])
        self.assertEqual(review['assessments'][0]['evidence'][0]['quote'], self.sources['003']['steps']['S01'])

    def test_unknown_reference_blocks_even_when_verdict_is_not_supported(self):
        row = self.review['assessments'][0]
        del row['evidence']
        row['evidence_refs'] = ['999/S01']
        row['verdict'] = '부분 지지'
        review = recover_review(self.review, self.claims, self.sources)
        self.assertFalse(review['passed'])
        self.assertTrue(review['assessments'][0]['unverified'])

    def test_recovery_uses_saved_analysis_snapshot_without_model(self):
        (self.root / 'validation_input.json').write_text(json.dumps({
            'claims': self.claims, 'analysis': {'003': SOURCE}}, ensure_ascii=False))
        raw = json.dumps(self.review, ensure_ascii=False)
        (self.root / 'validation_raw_response.txt').write_text(raw)
        review = recover_saved_review(self.root)
        self.assertTrue(review['passed'])
        self.assertEqual((self.root / 'validation_raw_response.txt').read_text(), raw)
        self.assertTrue((self.root / 'validation.md').is_file())

    def test_invalid_model_review_preserves_raw(self):
        client = SimpleNamespace(models=Mock())
        client.models.generate_content.return_value = SimpleNamespace(text='{"assessments": [], "coverage_findings": []}')
        review = review_policy(client, '### G-T1: 행동\n- Action: A', '### G-T1: 행동\n- 행동: A', self.sources, self.root)
        self.assertTrue((self.root / 'validation_raw_response.txt').is_file())
        self.assertFalse(review['passed'])
        self.assertGreater(review['integrity']['unverified_count'], 0)
        self.assertTrue((self.root / 'validation.json').exists())


class SelectionTests(unittest.TestCase):
    def select(self, bad=(), findings=None, preamble=False):
        text = ('# 원칙\n항상 설명한다\n' if preamble else '') + (
            '### G-T1: 정상\n- Action: A\n'
            '### G-T2: 문제 규칙\n- Trigger: B\n- Action: C\n'
            '### SEQ-1: 연결\n- Action Sequence: G-T2 다음 A\n'
            '### SEQ-2: 후속\n- Action Sequence: SEQ-1 다음 A\n')
        claims = build_claims(text, text)
        review = {'assessments': [dict(claim_id=c['id'], verdict=(
            '부분 지지' if c['id'] in bad else '지지됨')) for c in claims],
            'coverage_findings': findings or []}
        return select_supported_policies(text, text, review)

    def test_bad_field_removes_both_documents_and_transitive_dependencies(self):
        detailed, runtime, selection = self.select(bad=('runtime/G-T2/condition',))
        self.assertEqual(selection['kept_policy_ids'], ['G-T1'])
        self.assertTrue(selection['publishable'])
        for text in (detailed, runtime):
            self.assertNotIn('G-T2', text)
            self.assertNotIn('SEQ-', text)

    def test_unsupported_principles_replaced_not_published(self):
        detailed, runtime, selection = self.select(
            bad=('runtime/DOCUMENT/principles',), preamble=True)
        self.assertNotIn('항상 설명한다', runtime)
        self.assertNotIn('항상 설명한다', detailed)
        self.assertTrue(selection['publishable'])

    def test_localized_finding_excludes_rule_global_conflict_blocks(self):
        _, _, selection = self.select(findings=[dict(verdict='부분 지지', reason='G-T2 통합 오류')])
        self.assertEqual(selection['kept_policy_ids'], ['G-T1'])
        _, _, selection = self.select(findings=[dict(verdict='근거와 충돌', reason='문서 전체 조건 모순')])
        self.assertFalse(selection['publishable'])


if __name__ == '__main__':
    unittest.main()
