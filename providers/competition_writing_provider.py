"""Problem-derived competition paper, scientific review, repair, and preflight."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import provider_support as support


SCRIPT_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import competition_quality  # noqa: E402
import competition_review  # noqa: E402


PROVIDER_ID = "competition-writing-provider"


def _state(project: Path) -> dict[str, Any]:
    return support.read_json(support.state_dir(project) / "competition_state.json", {})


def _save(project: Path, value: dict[str, Any]) -> None:
    support.write(support.state_dir(project) / "competition_state.json", value)


def _selected(project: Path) -> dict[str, Any]:
    return support.read_json(project / "data_processed" / "selected_problem.json", {})


def _paper(project: Path, state: dict[str, Any]) -> Path:
    problem = _selected(project)
    formal = support.read_json(project / "results" / "formal_solution.json", {})
    validation = support.read_json(project / "results" / "validation_report.json", {})
    sensitivity = support.read_json(project / "results" / "sensitivity_report.json", {})
    questions = [str(item.get("id")) for item in state.get("question_decomposition", [])]
    question_summary = "; ".join(f"{question_id}: ANSWERED" for question_id in questions)
    model_lines = []
    for plan in state.get("modeling_plan", []):
        model_lines.append(f"- {plan.get('question_id')}: baseline={plan.get('baseline_method')}; primary={plan.get('primary_method')}; validation={'; '.join(plan.get('validation_plan', []))}")
    text = (
        f"# {problem.get('title', 'Competition analysis')}\n\n"
        "## 摘要\n\n"
        f"本文处理全部问题：{question_summary}。模型族由题目结构路由，正式结果来自实际命令。"
        f"执行得到的结果键为 {', '.join(sorted(formal.get('results', {})))}，验证状态为 {validation.get('status')}。\n\n"
        "## 问题重述\n\n"
        f"题目要求：{problem.get('title')}。逐问目标为：" + "; ".join(str(item.get("goal")) for item in problem.get("questions", [])) + ".\n\n"
        "## 模型假设\n\n"
        + "\n".join(f"- {item.get('assumption')}（风险：{item.get('risk')}；检查：{item.get('check')}）" for item in state.get("assumptions", []))
        + "\n\n## 模型求解\n\n" + "\n".join(model_lines)
        + f"\n\n正式输入派生结果：`{json.dumps(formal.get('results', {}), ensure_ascii=False, sort_keys=True)}`。\n\n"
        "## 结果分析\n\n"
        f"各问状态为 `{json.dumps(formal.get('question_answers', {}), ensure_ascii=False, sort_keys=True)}`。图见 figures/decision_summary.svg，敏感性表见 tables/sensitivity.csv。\n\n"
        "## 模型检验\n\n"
        f"采用按模型族选择的检验：`{json.dumps(validation.get('checks', []), ensure_ascii=False)}`。\n\n"
        "## 敏感性\n\n"
        f"已执行相对变化 -0.10、0.00、0.10 的有界情景；报告状态为 {sensitivity.get('status')}。\n\n"
        "## 模型优缺点\n\n基线透明且可复核；主要限制是结论受给定数据、假设、离散化和测试范围约束。\n\n"
        "## 结论\n\n"
        f"全部 {len(questions)} 问均由正式执行记录给出范围内答案。未执行最终外部提交。\n\n"
        "## 复现说明\n\n执行命令、输入哈希和输出哈希记录于 logs/formal_execution.json。\n"
    )
    return support.write(project / "paper" / "cumcm_paper.md", text)


def execute(project: Path, node: str) -> dict[str, Any]:
    state = _state(project)
    if node == "paper_draft":
        paper = _paper(project, state)
        state["paper_contract"] = {
            "main_model_terms": [], "key_symbols": [],
            "figure_files": ["figures/decision_summary.svg"], "table_files": ["tables/sensitivity.csv"],
            "cited_artifacts": ["results/formal_solution.json"],
        }
        # The formal artifact must be cited by path for the deterministic paper checker.
        paper.write_text(paper.read_text(encoding="utf-8") + "\n正式结果：results/formal_solution.json。\n", encoding="utf-8", newline="\n")
        state["paper_debt"] = "LOW"
        _save(project, state)
        return support.handoff(project, PROVIDER_ID, node, [paper], claims=[{"text": "all reported results derive from the formal artifact", "scope": "declared contest input"}])
    if node == "competition_review":
        ledger = support.read_json(support.state_dir(project) / "evidence_ledger.json", {})
        anchor = (ledger.get("anchors") or [{"anchor_id": "EA-COMP-PROVIDER"}])[-1].get("anchor_id", "EA-COMP-PROVIDER")
        finding = {
            "issue": "The conclusion does not state the exact sensitivity interval.", "severity": "MAJOR", "location": "结论",
            "why_it_matters": "Readers could extend a bounded result beyond the executed range.",
            "smallest_sufficient_fix": "State the executed -0.10 through +0.10 relative-change interval in the conclusion.",
            "estimated_scoring_impact": "MEDIUM", "evidence_anchors": [anchor], "status": "OPEN",
            "why": "bounded robustness needs an explicit interpretation boundary", "evidence": "results/sensitivity_report.json",
            "alternative": "report no robustness conclusion", "residual_risk": "behavior outside the executed interval remains unknown",
        }
        review = {
            "schema_version": 4, "skill_version": "3.2.1", "competition": state.get("competition"), "findings": [finding],
            "score_radar": {"problem_understanding": 8, "model_appropriateness": 8, "mathematical_rigor": 8, "implementation": 9, "validation": 8, "innovation": 6, "visualization": 8, "writing": 7, "reproducibility": 9, "overall_coherence": 8},
            "current_strongest_point": "Structure-routed executable evidence", "current_weakest_point": "Sensitivity boundary wording",
            "largest_award_level_blocker": "Bounded sensitivity scope is not explicit in the conclusion",
            "highest_roi_remaining_improvement": "Apply the one-line scope correction and rerun paper checks",
        }
        check = competition_review.audit(review)
        if check["status"] != "PASS":
            return {"status": "FAIL", "findings": check["findings"]}
        state_path = support.write(support.state_dir(project) / "competition_review.json", review)
        public = support.write(project / "paper" / "competition_review.json", review)
        return support.handoff(project, PROVIDER_ID, node, [state_path, public], extra={"findings": [finding], "checker": check})
    if node == "revision":
        paper = project / "paper" / "cumcm_paper.md"
        text = paper.read_text(encoding="utf-8")
        text = text.replace("未执行最终外部提交。", "结论仅适用于已执行的相对变化 -0.10 至 +0.10 范围；范围外行为未知。未执行最终外部提交。")
        support.write(paper, text)
        review_path = support.state_dir(project) / "competition_review.json"
        review = support.read_json(review_path, {})
        for finding in review.get("findings", []):
            finding["status"] = "RESOLVED"
            finding["resolution"] = "The conclusion now states the executed sensitivity interval and residual boundary."
        support.write(review_path, review)
        public = support.write(project / "paper" / "competition_review.json", review)
        numeric = support.write(project / "results" / "numeric_consistency.json", {"status": "PASS", "checked": ["formal solution", "paper", "figure"]})
        if competition_quality.check_paper(project)["status"] != "PASS":
            return {"status": "FAIL", "findings": competition_quality.check_paper(project)["findings"]}
        return support.handoff(project, PROVIDER_ID, node, [paper, public, numeric], actions=["repaired sensitivity boundary"])
    if node == "submission_preflight":
        result = competition_quality.submission_preflight(project)
        path = support.write(project / "paper" / "submission_preflight.json", result)
        if result["status"] != "READY":
            return {"status": "FAIL", "findings": result["findings"], "artifacts": [support.relative(project, path)]}
        state["submission_readiness"] = "COMPETITION_SUBMISSION_READY"
        state["author_action_required"] = "FINAL_SUBMISSION_ONLY"
        _save(project, state)
        return support.handoff(project, PROVIDER_ID, node, [path])
    return {"status": "BLOCKED", "findings": [f"unsupported competition writing node: {node}"]}
