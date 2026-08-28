#!/usr/bin/env python3
"""Legacy logistics fixture provider retained only for explicit competition E2E."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


SKILL_VERSION = "3.2.0"
SCRIPT_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import competition_method_router  # noqa: E402
import competition_problem  # noqa: E402
import competition_quality  # noqa: E402
import competition_review  # noqa: E402


def _state(project: Path) -> Path:
    project = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project / name
        if candidate.exists():
            return candidate
    raise RuntimeError("research state is missing")


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def _competition_input(project: Path) -> dict[str, Any]:
    state_path = _state(project) / "competition_input.json"
    root_path = project / "competition_input.json"
    path = state_path if state_path.is_file() else root_path
    value = _read(path, {})
    if not isinstance(value, dict) or not isinstance(value.get("problems"), list):
        raise RuntimeError("competition input with a problems list is required")
    return value


def _load_state(project: Path) -> dict[str, Any]:
    return _read(_state(project) / "competition_state.json", {})


def _save_state(project: Path, value: dict[str, Any]) -> None:
    _write(_state(project) / "competition_state.json", value)


def _artifact_manifest(project: Path, paths: list[Path], node_id: str) -> None:
    manifest_path = _state(project) / "artifact_manifest.json"
    manifest = _read(manifest_path, {})
    artifacts = manifest.setdefault("artifacts", [])
    known = {item.get("path") for item in artifacts if isinstance(item, dict)}
    for path in paths:
        relative = _relative(project, path)
        if relative in known:
            continue
        artifacts.append(
            {
                "id": f"COMP-{node_id.upper()}-{len(artifacts) + 1:03d}",
                "path": relative,
                "type": "competition_output",
                "sha256": _sha256(path),
                "created_by": f"competition-executor:{node_id}",
                "status": "OBSERVED",
            }
        )
    _write(manifest_path, manifest)


def _record_evidence(project: Path, node_id: str, artifact: Path) -> str:
    digest = _sha256(artifact)
    anchor_id = f"EA-COMP-{node_id.upper().replace('_', '-')}-{digest[7:19]}"
    ledger_path = _state(project) / "evidence_ledger.json"
    ledger = _read(ledger_path, {})
    anchors = ledger.setdefault("anchors", [])
    if not any(item.get("anchor_id") == anchor_id for item in anchors):
        anchors.append(
            {
                "anchor_id": anchor_id,
                "claim_id": "COMPETITION-RUNTIME",
                "result_id": f"R-{node_id.upper()}",
                "source_artifact": f"{_relative(project, artifact)}#{digest}",
                "source_sha256": digest.removeprefix("sha256:"),
                "exact_region": "complete generated artifact",
                "transformation": f"competition executor handler: {node_id}",
                "uncertainty": "bounded to supplied contest data, declared assumptions, and deterministic execution",
                "scope": "competition project runtime",
                "status": "OBSERVED",
                "provenance_level": "OBSERVED",
                "artifact_type": "competition_output",
                "artifact_acquisition_record_id": f"competition-executor:{node_id}",
            }
        )
        _write(ledger_path, ledger)
    return anchor_id


def _contest_intake(project: Path) -> list[Path]:
    try:
        source = _competition_input(project)
    except RuntimeError:
        # Backward-compatible intake can inventory an initialized competition
        # project before the author supplies problem files. Downstream
        # decomposition remains fail-closed until real problems exist.
        source = {
            "competition": "CUMCM",
            "problems": [],
            "rules": [],
            "official_rules_source": "",
            "intake_status": "AWAITING_PROBLEMS",
        }
    for directory in (
        "src", "data", "data_raw", "data_processed", "results", "figures",
        "tables", "configs", "logs", "paper", "artifacts/competition",
    ):
        (project / directory).mkdir(parents=True, exist_ok=True)
    raw = project / "data_raw" / "contest_input.json"
    _write(raw, source)
    intake = project / "artifacts" / "competition" / "contest_intake.json"
    _write(
        intake,
        {
            "competition": source.get("competition", "CUMCM"),
            "problem_ids": [item.get("id") for item in source["problems"]],
            "rule_record_count": len(source.get("rules", [])),
            "official_rules_source": source.get("official_rules_source"),
            "status": "PASS",
        },
    )
    state = _load_state(project)
    risk_registry = _read(_state(project) / "competition_risks.json", {"risks": []})
    state.update(
        {
            "competition": source.get("competition", "CUMCM"),
            "available_problems": [item.get("id") for item in source["problems"]],
            "paper_debt": "LOW",
            "validation_debt": "HIGH",
            "complexity_debt": "LOW",
            "competition_risks": risk_registry.get("risks", []),
        }
    )
    _save_state(project, state)
    return [intake, raw]


def _problem_decomposition(project: Path) -> list[Path]:
    result = competition_problem.decompose(_competition_input(project)["problems"])
    if result["status"] != "PASS":
        raise RuntimeError("problem decomposition failed: " + "; ".join(result["findings"]))
    path = project / "artifacts" / "competition" / "problem_decomposition.json"
    _write(path, result)
    state = _load_state(project)
    state["problem_decompositions"] = result["problems"]
    _save_state(project, state)
    return [path]


def _problem_selection(project: Path) -> list[Path]:
    source = _competition_input(project)
    result = competition_problem.select(source["problems"])
    if result["decision"] != "AUTO_SELECT":
        raise RuntimeError("automatic problem selection requires author input")
    selected = next(item for item in source["problems"] if item["id"] == result["selected_problem"])
    path = project / "artifacts" / "competition" / "problem_selection.json"
    processed = project / "data_processed" / "selected_problem.json"
    _write(path, result)
    _write(processed, selected)
    state = _load_state(project)
    state["selected_problem"] = selected["id"]
    state["problem_selection"] = result
    decomposition = next(
        item for item in state["problem_decompositions"] if item["problem_id"] == selected["id"]
    )
    state["question_decomposition"] = decomposition["questions"]
    state["question_graph"] = decomposition["question_graph"]
    state["largest_scoring_risk"] = result["largest_selection_risk"]
    _save_state(project, state)
    return [path, processed]


def _assumptions(project: Path) -> list[Path]:
    state = _load_state(project)
    assumptions = [
        {
            "id": "A-1",
            "assumption": "The supplied observations and constraints describe the requested contest scenario.",
            "reason": "The synthetic fixture is the authoritative problem input.",
            "evidence_source": "data_raw/contest_input.json",
            "consequence": "The model can operate on one frozen input snapshot.",
            "risk_if_violated": "The forecast or selected facility may no longer be feasible.",
            "affected_equations_models": ["linear trend forecast", "capacity-constrained enumeration"],
            "validation_or_sensitivity": "perturb demand by -10%, -5%, +5%, and +10%",
            "affected_questions": [question["id"] for question in state["question_decomposition"]],
        }
    ]
    state["assumptions"] = assumptions
    _save_state(project, state)
    path = project / "artifacts" / "competition" / "assumption_contract.json"
    _write(path, {"status": "PASS", "assumptions": assumptions})
    return [path]


def _method_candidates(project: Path) -> list[Path]:
    state = _load_state(project)
    task = "; ".join(question["goal"] for question in state["question_decomposition"])
    route = competition_method_router.route(task)
    if route["status"] not in {"PASS", "CONDITIONAL"}:
        raise RuntimeError("method routing failed")
    path = project / "artifacts" / "competition" / "method_route.json"
    _write(path, route)
    state["candidate_models"] = route["candidate_models"]
    state["method_route"] = route
    state["baseline_model"] = "last-observation forecast plus exhaustive feasible-site enumeration"
    state["primary_model"] = "linear-trend forecast plus exhaustive feasible-site enumeration"
    state["paper_contract"] = {
        "main_model_terms": ["末值基线", "线性趋势预测", "可行点穷举"],
        "key_symbols": ["$D$", "$C$", "$J$"],
        "figure_files": ["figures/decision_summary.svg"],
        "table_files": ["tables/sensitivity.csv"],
        "cited_artifacts": [
            "data_processed/selected_problem.json",
            "logs/formal_execution.json",
        ],
    }
    _save_state(project, state)
    return [path]


MODEL_SOURCE = r'''#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def solve(problem, factor):
    history = [float(value) for value in problem["demand_history"]]
    baseline = history[-1]
    differences = [right - left for left, right in zip(history, history[1:])]
    forecast = (history[-1] + sum(differences) / len(differences)) * factor
    candidates = []
    distance_cost_rate = float(problem.get("distance_cost_rate", 0.01))
    for site in problem["sites"]:
        feasible = float(site["capacity"]) >= forecast
        total_cost = float(site["fixed_cost"]) + float(site["distance"]) * forecast * distance_cost_rate
        candidates.append({
            "site": site["id"], "capacity": site["capacity"], "forecast_demand": round(forecast, 6),
            "feasible": feasible, "total_cost": round(total_cost, 6)
        })
    feasible = [item for item in candidates if item["feasible"]]
    if not feasible:
        raise RuntimeError("no feasible facility")
    selected = min(feasible, key=lambda item: (item["total_cost"], item["site"]))
    return {
        "status": "PASS", "baseline_forecast": baseline, "forecast_demand": round(forecast, 6),
        "selected_site": selected["site"], "selected_total_cost": selected["total_cost"],
        "candidates": candidates, "objective_recalculated": selected["total_cost"],
        "units": {"demand": "units/period", "capacity": "units/period", "cost": "cost-units"}
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--demand-factor", type=float, default=1.0)
    args = parser.parse_args()
    problem = json.loads(args.input.read_text(encoding="utf-8"))
    result = solve(problem, args.demand_factor)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
'''


def _minimal_viable_model(project: Path) -> list[Path]:
    source = project / "src" / "run.py"
    config = project / "configs" / "formal.json"
    _write_text(source, MODEL_SOURCE)
    _write(
        config,
        {
            "input": "data_processed/selected_problem.json",
            "method": "linear trend plus exhaustive enumeration",
            "seed": None,
            "validation": ["feasibility", "objective recalculation", "sensitivity"],
            "phase": "FORMAL",
        },
    )
    contract = project / "artifacts" / "competition" / "mvp_implementation.json"
    _write(
        contract,
        {
            "status": "PASS",
            "entrypoint": "python src/run.py",
            "baseline_first": True,
            "dependencies": "Python standard library only",
            "code_sha256": _sha256(source),
        },
    )
    return [contract, source, config]


def _run_model(project: Path, *, phase: str, factor: float, output: Path) -> tuple[Path, Path]:
    source = project / "src" / "run.py"
    source_input = project / "data_processed" / "selected_problem.json"
    command = [
        sys.executable, str(source), "--input", str(source_input), "--output",
        str(output), "--demand-factor", str(factor),
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=project, capture_output=True, text=True, timeout=30, check=False
    )
    runtime = time.perf_counter() - started
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(f"{phase} execution failed: {completed.stderr.strip()}")
    record = project / "logs" / f"{phase.lower()}_execution.json"
    config = project / "configs" / "formal.json"
    _write(
        record,
        {
            "phase": phase,
            "command": command,
            "exit_code": completed.returncode,
            "runtime_seconds": runtime,
            "input_sha256": _sha256(source_input),
            "config_sha256": _sha256(config),
            "code_sha256": _sha256(source),
            "code_commit": os.environ.get("GITHUB_SHA", "working-tree"),
            "environment": {"python": platform.python_version(), "platform": platform.platform()},
            "output_sha256": _sha256(output),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    )
    return output, record


def _pilot_solve(project: Path) -> list[Path]:
    output, record = _run_model(
        project, phase="PILOT", factor=1.0, output=project / "results" / "pilot_solution.json"
    )
    state = _load_state(project)
    state["baseline_result"] = _read(output, {})
    state["baseline_available"] = True
    _save_state(project, state)
    return [output, record]


def _model_validation(project: Path) -> list[Path]:
    result = _read(project / "results" / "pilot_solution.json", {})
    problem = _read(project / "data_processed" / "selected_problem.json", {})
    solver_check = competition_quality.check_solver_result(problem, result)
    selected = next(
        (item for item in result.get("candidates", []) if item.get("site") == result.get("selected_site")), {}
    )
    feasible = bool(selected.get("feasible"))
    objective_ok = result.get("selected_total_cost") == result.get("objective_recalculated")
    dimensions = competition_quality.check_dimensions(
        symbols=[
            {"variable": "demand", "symbol": "D", "meaning": "forecast demand", "unit": "units/period", "range": ">=0", "source": "executed forecast"},
            {"variable": "capacity", "symbol": "C", "meaning": "facility capacity", "unit": "units/period", "range": ">=0", "source": "problem data"},
            {"variable": "cost", "symbol": "J", "meaning": "total decision cost", "unit": "cost-units", "range": ">=0", "source": "executed objective"},
        ],
        equations=[
            {"id": "capacity-feasibility", "left_unit": "units/period", "right_unit": "units/period", "core": True},
            {"id": "objective", "left_unit": "cost-units", "right_unit": "cost-units", "core": True},
        ],
    )
    report = {
        "status": "PASS" if feasible and objective_ok and dimensions["status"] == "PASS" and solver_check["status"] == "PASS" else "FAIL",
        "constraint_feasibility": feasible,
        "bounds": result.get("forecast_demand", -1) >= 0,
        "non_negativity": result.get("selected_total_cost", -1) >= 0,
        "capacity": selected.get("capacity", -1) >= result.get("forecast_demand", 10**9),
        "objective_recalculation": objective_ok,
        "boundary_cases": "checked by capacity inequality and later demand perturbations",
        "baseline_comparison": {"baseline_forecast": result.get("baseline_forecast"), "primary_forecast": result.get("forecast_demand")},
        "residual_diagnostics": "linear increments are constant in the synthetic fixture",
        "error_analysis": "largest forecast risk is departure from the recent linear increment; decision impact is tested by scenarios",
        "solver_sanity": solver_check,
        "findings": dimensions["findings"] + solver_check["findings"],
    }
    path = project / "results" / "validation_report.json"
    unit_path = project / "results" / "unit_check.json"
    _write(path, report)
    _write(unit_path, dimensions)
    if report["status"] != "PASS":
        raise RuntimeError("pilot validation failed")
    return [path, unit_path]


def _formal_solve(project: Path) -> list[Path]:
    output, record = _run_model(
        project, phase="FORMAL", factor=1.0, output=project / "results" / "formal_solution.json"
    )
    state = _load_state(project)
    result = _read(output, {})
    state["formal_result"] = result
    state["current_best_model"] = state.get("primary_model")
    state["question_answers"] = {
        question["id"]: {
            "answer": (
                f"selected site {result['selected_site']} at total cost {result['selected_total_cost']} cost-units"
                if index in {0, 2}
                else f"forecast demand is {result['forecast_demand']} units/period"
                if index == 1
                else "recommendation stability is evaluated by declared sensitivity scenarios"
            ),
            "result_id": "FORMAL-SOLUTION",
            "evidence": _sha256(output),
        }
        for index, question in enumerate(state["question_decomposition"])
    }
    _save_state(project, state)
    return [output, record]


def _sensitivity_robustness(project: Path) -> list[Path]:
    scenarios: list[dict[str, Any]] = []
    generated: list[Path] = []
    for factor in (0.90, 0.95, 1.0, 1.05, 1.10):
        label = str(factor).replace(".", "_")
        output, record = _run_model(
            project, phase=f"SENSITIVITY_{label}", factor=factor,
            output=project / "results" / "scenarios" / f"demand_{label}.json",
        )
        value = _read(output, {})
        scenarios.append(
            {
                "factor": factor, "decision": value["selected_site"],
                "forecast_demand": value["forecast_demand"],
                "selected_total_cost": value["selected_total_cost"],
                "relative_change": abs(factor - 1.0), "output_sha256": _sha256(output),
            }
        )
        generated.extend([output, record])
    formal = _read(project / "results" / "formal_solution.json", {})
    classification = competition_quality.classify_sensitivity(formal["selected_site"], scenarios)
    report = classification | {
        "status": "PASS",
        "load_bearing_parameters": ["forecast demand", "facility capacity", "distance cost rate"],
        "uncertain_parameters": ["next-period demand"],
        "assumed_parameters": ["distance cost rate"],
        "estimated_parameters": ["linear demand increment"],
        "scenarios": scenarios,
        "robustness": ["alternative demand windows", "low/baseline/high demand"],
        "error_analysis": "No decision reversal occurs in the justified range; capacity is the closest boundary.",
    }
    report_path = project / "results" / "sensitivity_report.json"
    table_path = project / "tables" / "sensitivity.csv"
    _write(report_path, report)
    rows = ["factor,forecast_demand,selected_site,selected_total_cost"] + [
        f"{item['factor']},{item['forecast_demand']},{item['decision']},{item['selected_total_cost']}"
        for item in scenarios
    ]
    _write_text(table_path, "\n".join(rows) + "\n")
    state = _load_state(project)
    state["sensitivity"] = report
    state["validation_debt"] = "LOW"
    _save_state(project, state)
    return [report_path, table_path] + generated


def _model_improvement(project: Path) -> list[Path]:
    state = _load_state(project)
    decision = {
        "status": "PASS",
        "decision": "KEEP_PRIMARY_SIMPLE_MODEL",
        "baseline_defect": "last-observation forecast ignores the stable recent trend",
        "evidence_of_defect": "four supplied observations increase by a constant increment",
        "improvement": "linear increment forecast captures the observed trend",
        "validation_improvement": "scenario checks preserve the selected facility",
        "complexity_worth_it": True,
        "innovation_claim": "problem-specific transparent formulation, not algorithm-name novelty",
    }
    path = project / "results" / "model_improvement_decision.json"
    _write(path, decision)
    state["complexity_debt"] = "LOW"
    _save_state(project, state)
    return [path]


FIGURE_SOURCE = r'''#!/usr/bin/env python3
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
output = Path(sys.argv[2])
values = [(item["site"], item["total_cost"], item["feasible"]) for item in result["candidates"]]
bars = []
for index, (site, cost, feasible) in enumerate(values):
    x = 80 + index * 120
    height = cost * 8
    color = "#2471A3" if site == result["selected_site"] else ("#7F8C8D" if feasible else "#C0392B")
    bars.append(f'<rect x="{x}" y="{300-height:.2f}" width="70" height="{height:.2f}" fill="{color}"/><text x="{x+35}" y="325" text-anchor="middle">{site}</text><text x="{x+35}" y="{290-height:.2f}" text-anchor="middle">{cost:.2f}</text>')
svg = '<svg xmlns="http://www.w3.org/2000/svg" width="520" height="380" viewBox="0 0 520 380"><rect width="100%" height="100%" fill="white"/><text x="260" y="28" text-anchor="middle" font-size="18">Feasible facility cost comparison</text><line x1="55" y1="300" x2="455" y2="300" stroke="black"/><line x1="55" y1="55" x2="55" y2="300" stroke="black"/><text x="18" y="180" transform="rotate(-90 18 180)">Total cost (cost-units)</text>' + ''.join(bars) + '<text x="260" y="360" text-anchor="middle">Selected facility is highlighted in blue; red is infeasible.</text></svg>'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(svg, encoding="utf-8")
'''


def _visualization(project: Path) -> list[Path]:
    script = project / "src" / "render_figure.py"
    figure = project / "figures" / "decision_summary.svg"
    source = project / "results" / "formal_solution.json"
    _write_text(script, FIGURE_SOURCE)
    completed = subprocess.run(
        [sys.executable, str(script), str(source), str(figure)], cwd=project,
        capture_output=True, text=True, timeout=30, check=False,
    )
    if completed.returncode != 0 or not figure.is_file():
        raise RuntimeError("figure rendering failed")
    manifest = {
        "status": "PASS",
        "figures": [
            {
                "path": _relative(project, figure), "source_data": _relative(project, source),
                "code": _relative(project, script), "artifact_sha256": _sha256(figure),
                "source_sha256": _sha256(source), "code_sha256": _sha256(script),
                "proves": "the selected feasible facility has the lowest recalculated objective among feasible candidates",
                "axis": "candidate facility and total cost", "unit": "cost-units",
                "legend": "blue selected, gray feasible alternative, red infeasible",
                "caption": "Executed formal-solution cost comparison with feasibility encoded by color.",
                "font_size": "readable", "resolution": "vector SVG", "cropping": "viewBox 0 0 520 380",
            }
        ],
    }
    manifest_path = project / "figures" / "figure_manifest.json"
    _write(manifest_path, manifest)
    check = competition_quality.check_figure_traceability(project, manifest)
    if check["status"] != "PASS":
        raise RuntimeError("figure traceability failed: " + "; ".join(check["findings"]))
    return [figure, manifest_path, script]


def _paper_text(state: dict[str, Any], result: dict[str, Any]) -> str:
    sensitivity = state.get("sensitivity", {})
    answers = state.get("question_answers", {})
    answer_lines = "\n".join(
        f"- **{question_id}**：{record['answer']}" for question_id, record in answers.items()
    )
    return f"""# CUMCM 合成赛题论文

## 摘要
本文回答 {', '.join(answers)}。采用末值基线与线性趋势预测，并以可行点穷举完成容量约束选址。正式执行得到需求预测 {result['forecast_demand']} units/period，选择站点 {result['selected_site']}，总成本 {result['selected_total_cost']} cost-units。±10% 需求情景下结论保持不变，敏感性分类为 {sensitivity.get('classification', 'stable')}。

## 问题重述
评价候选点、预测下一周期需求、优化设施选择，并验证建议的敏感性与稳健性。

## 问题分析
先建立透明基线，再用最小必要复杂度捕捉近期趋势；优化部分使用可穷举的小规模精确方法。

## 模型假设
输入数据代表当前情景；假设的后果、风险和敏感性范围记录于 assumption contract。

## 符号说明
$D$ 为需求（units/period），$C$ 为容量（units/period），$J$ 为总成本（cost-units）。

## 数据处理
保留原始输入哈希，并将所选题目冻结于 `data_processed/selected_problem.json`。

## 模型建立
预测采用最近增量均值；选址目标是在 $C \\ge D$ 下最小化 $J$。

## 模型求解
正式入口为 `python src/run.py`，真实执行记录保存在 `logs/formal_execution.json`。

## 结果分析
{answer_lines}

## 模型检验
独立检查容量可行性、非负性、目标重算、量纲和边界情景，均通过。

## 敏感性与稳健性
需求因子 0.90、0.95、1.00、1.05、1.10 均已实际运行；分类为 {sensitivity.get('classification', 'stable')}。
完整情景表见 `tables/sensitivity.csv`。

## 图表
![正式求解的候选点成本与可行性比较](../figures/decision_summary.svg)
图源文件为 `figures/decision_summary.svg`，其数据、代码与哈希记录于 figure manifest。

## 模型优缺点
优点是透明、可复现、无需难安装依赖；限制是小样本趋势不能代表长期结构变化。

## 结论
预测需求 {result['forecast_demand']} units/period，选择站点 {result['selected_site']}，总成本 {result['selected_total_cost']} cost-units；该建议在声明情景内稳定。

## 参考文献
本合成 E2E 不使用外部事实或虚构引用。

## 附录
代码、配置、执行记录、结果、图和哈希清单均随项目保存。
"""


def _paper_draft(project: Path) -> list[Path]:
    state = _load_state(project)
    result = _read(project / "results" / "formal_solution.json", {})
    paper = project / "paper" / "cumcm_paper.md"
    _write_text(paper, _paper_text(state, result))
    state["paper_debt"] = "LOW"
    _save_state(project, state)
    return [paper]


def _competition_review(project: Path) -> list[Path]:
    ledger = _read(_state(project) / "evidence_ledger.json", {})
    anchor = ledger.get("anchors", [{}])[-1].get("anchor_id", "EA-COMP-UNKNOWN")
    review = {
        "schema_version": 4,
        "skill_version": SKILL_VERSION,
        "competition": "CUMCM",
        "findings": [
            {
                "issue": "The conclusion should explicitly bind the stability statement to the tested demand range.",
                "severity": "MAJOR", "location": "结论",
                "why_it_matters": "Readers could otherwise overgeneralize a bounded sensitivity result.",
                "evidence": "results/sensitivity_report.json",
                "smallest_sufficient_fix": "Add the tested 0.90–1.10 demand-factor scope to the conclusion.",
                "estimated_scoring_impact": "MEDIUM",
                "residual_risk": "Behavior outside the tested range remains unknown.",
                "evidence_anchors": [anchor], "status": "OPEN",
            }
        ],
        "score_radar": {
            "problem_understanding": 8, "model_appropriateness": 8,
            "mathematical_rigor": 8, "implementation": 9, "validation": 8,
            "innovation": 6, "visualization": 8, "writing": 7,
            "reproducibility": 9, "overall_coherence": 8,
        },
        "current_strongest_point": "Executable evidence and independent feasibility checks",
        "current_weakest_point": "Sensitivity scope wording",
        "largest_award_level_blocker": "Bounded sensitivity scope is not explicit in the conclusion",
        "highest_roi_remaining_improvement": "Apply the one-line scope correction and recheck numbers",
    }
    check = competition_review.audit(review)
    if check["status"] != "PASS":
        raise RuntimeError("competition review contract failed")
    path = _state(project) / "competition_review.json"
    public_path = project / "paper" / "competition_review.json"
    _write(path, review)
    _write(public_path, review)
    return [public_path]


def _revision(project: Path) -> list[Path]:
    paper = project / "paper" / "cumcm_paper.md"
    text = paper.read_text(encoding="utf-8")
    text = text.replace(
        "该建议在声明情景内稳定。",
        "该建议仅在已执行的需求因子 0.90–1.10 范围内保持稳定；范围外行为未知。",
    )
    _write_text(paper, text)
    review_path = _state(project) / "competition_review.json"
    review = _read(review_path, {})
    for finding in review.get("findings", []):
        finding["status"] = "RESOLVED"
        finding["resolution"] = "Conclusion now states the executed sensitivity range and residual boundary."
    _write(review_path, review)
    _write(project / "paper" / "competition_review.json", review)
    formal = _read(project / "results" / "formal_solution.json", {})
    numeric = competition_quality.check_numeric_consistency(
        {
            "abstract": {"forecast_demand": formal["forecast_demand"], "selected_total_cost": formal["selected_total_cost"]},
            "results": {"forecast_demand": formal["forecast_demand"], "selected_total_cost": formal["selected_total_cost"]},
            "conclusion": {"forecast_demand": formal["forecast_demand"], "selected_total_cost": formal["selected_total_cost"]},
        }
    )
    numeric_path = project / "results" / "numeric_consistency.json"
    _write(numeric_path, numeric)
    paper_check = competition_quality.check_paper(project)
    if numeric["status"] != "PASS" or paper_check["status"] != "PASS":
        raise RuntimeError("revision consistency check failed")
    return [paper, numeric_path, project / "paper" / "competition_review.json"]


def _submission_preflight(project: Path) -> list[Path]:
    result = competition_quality.submission_preflight(project)
    path = project / "paper" / "submission_preflight.json"
    _write(path, result)
    if result["status"] != "READY":
        raise RuntimeError("submission preflight blocked: " + "; ".join(result["findings"]))
    state = _load_state(project)
    state["submission_readiness"] = result["submission_readiness"]
    state["author_action_required"] = "FINAL_SUBMISSION_ONLY"
    _save_state(project, state)
    return [path]


HANDLERS: dict[str, Callable[[Path], list[Path]]] = {
    "contest_intake": _contest_intake,
    "problem_decomposition": _problem_decomposition,
    "problem_selection": _problem_selection,
    "assumptions": _assumptions,
    "method_candidates": _method_candidates,
    "minimal_viable_model": _minimal_viable_model,
    "pilot_solve": _pilot_solve,
    "model_validation": _model_validation,
    "formal_solve": _formal_solve,
    "sensitivity_robustness": _sensitivity_robustness,
    "model_improvement": _model_improvement,
    "visualization": _visualization,
    "paper_draft": _paper_draft,
    "competition_review": _competition_review,
    "revision": _revision,
    "submission_preflight": _submission_preflight,
}


def execute_node(project: Path, node_id: str) -> dict[str, Any]:
    """Execute one overlay-selected node; never transition the graph itself."""
    project = project.resolve()
    handler = HANDLERS.get(node_id)
    if handler is None:
        return {
            "operation": "competition-execute-node", "status": "FAIL", "node": node_id,
            "findings": ["no competition executor is registered for this node"],
        }
    try:
        artifacts = handler(project)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        return {
            "operation": "competition-execute-node", "status": "FAIL", "node": node_id,
            "findings": [str(exc)],
        }
    missing = [str(path) for path in artifacts if not path.is_file() or path.stat().st_size == 0]
    if missing:
        return {
            "operation": "competition-execute-node", "status": "FAIL", "node": node_id,
            "findings": [f"executor artifacts are missing or empty: {missing}"],
        }
    summary = project / "artifacts" / "competition" / f"{node_id}.json"
    _write(
        summary,
        {
            "node": node_id, "status": "PASS",
            "artifacts": [{"path": _relative(project, path), "sha256": _sha256(path)} for path in artifacts],
            "output_contract": "actual project-local artifacts checked before graph PASS",
        },
    )
    all_artifacts = [summary] + artifacts
    _artifact_manifest(project, all_artifacts, node_id)
    anchor_id = _record_evidence(project, node_id, summary)
    return {
        "operation": "competition-execute-node", "status": "PASS", "node": node_id,
        "artifacts": [_relative(project, path) for path in all_artifacts],
        "evidence": [anchor_id],
        "checker": {"status": "PASS", "artifact_sha256": _sha256(summary)},
    }
