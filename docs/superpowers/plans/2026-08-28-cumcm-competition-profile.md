# CUMCM Competition Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic CUMCM competition overlay to `cs-nature-paper` V3.1.1 with competition modes, clock-driven scheduling, method routing, review, and a synthetic end-to-end fixture.

**Architecture:** `competition_runtime.py` is a policy layer over the existing generic Research Graph and canonical provenance state. Competition initialization selects a compatible graph template and adds contest-only state projections; clock adjustments use their own append-only hash chain, while all scientific state remains in the existing claims, evidence, experiments, artifacts, and handoff files.

**Tech Stack:** Python 3.10+ standard library, JSON/JSONL, `unittest`, Markdown, GitHub Actions. No third-party runtime or test dependency.

## Global Constraints

- Preserve all existing V3.1.1 research-mode semantics and provenance/evidence contracts.
- Do not modify `scripts/research_graph.py` with CUMCM-specific branches.
- Do not modify or move tag `v3.1.1`; do not create V3.2/V4 or a release.
- Do not install another Skill or add a third-party dependency.
- `contest_start_utc` and `submission_deadline_utc` are timezone-aware ISO-8601 authority boundaries.
- `UNVERIFIED` clocks cannot authorize time-based graph mutations or new timed jobs.
- Every manual clock change is append-only and hash chained.
- `FINALIZATION_MODE` at six hours and `HARD_FREEZE` at two hours override normal scheduling.
- Competition state references, rather than copies, canonical claims, evidence, experiments, artifacts, and handoffs.
- Every production behavior starts with a failing test observed for the expected reason.
- Preserve all existing 57 regression tests.

---

## File Map

**Create:**

- `references/competitions/cumcm.md`: progressive-disclosure operating policy.
- `scripts/competition_runtime.py`: clock, phase mapping, policy scheduler, rules gate, dashboard, and CLI.
- `scripts/competition_method_router.py`: contest model-family selection and CLI.
- `scripts/competition_review.py`: contest findings and score-radar validation.
- `scripts/competition_smoke_run.py`: deterministic synthetic CUMCM E2E.
- `assets/competition/cumcm_profile.json`: machine-readable phases, margins, and node policies.
- `assets/registry/competition_method_router.json`: modeling categories and playbooks.
- `assets/templates/competition/*.json`: contest graph and state projections.
- `assets/schemas/competition_*.schema.json`: public contracts.
- `assets/fixtures/cumcm/synthetic_problem.json`: deterministic facility-selection fixture.
- `tests/test_competition_runtime.py`: focused unit/integration tests.
- `tests/test_competition_e2e.py`: synthetic workflow test.

**Modify:**

- `scripts/research_state.py`: recognize modes and initialize contest templates only.
- `scripts/validate_registry.py`: validate the competition method registry/profile.
- `SKILL.md`: route competition modes to the CUMCM reference and runtimes.
- `README.md`, `README_zh.md`: usage and architecture overview.
- `assets/evals/behavior_cases.json`: contest pressure cases.
- `.github/workflows/ci.yml`: run the competition smoke.
- `scripts/validate_release.py`, `scripts/build_manifest.py`, `SHA256SUMS.txt`: validate competition templates, exclude generated smoke output, and refresh source checksums using existing tooling.

---

### Task 1: Competition Initialization and Generic Graph Profile

**Files:**

- Create: `assets/competition/cumcm_profile.json`
- Create: `assets/templates/competition/competition_clock.json`
- Create: `assets/templates/competition/competition_state.json`
- Create: `assets/templates/competition/competition_rules.json`
- Create: `assets/templates/competition/research_graph.json`
- Create: `assets/templates/competition/competition_review.json`
- Create: `assets/schemas/competition_profile.schema.json`
- Create: `assets/schemas/competition_clock.schema.json`
- Create: `assets/schemas/competition_state.schema.json`
- Create: `assets/schemas/competition_rules.schema.json`
- Create: `assets/schemas/competition_review.schema.json`
- Modify: `scripts/research_state.py`
- Test: `tests/test_competition_runtime.py`

**Interfaces:**

- Produces: `research_state.COMPETITION_MODES: tuple[str, ...]`
- Produces: `research_state.init_state(project_dir, study_type, mode, domain)` with contest-only template selection.
- Produces: `.research-state/competition_clock.json`, `competition_state.json`, `competition_rules.json`, and `competition_review.json` only for competition modes.

- [ ] **Step 1: Write failing initialization tests**

```python
class CompetitionInitializationTests(unittest.TestCase):
    def test_competition_mode_selects_contest_graph_and_state(self):
        research_state.init_state(self.project, "algorithmic", "competition", "mathematical-modeling")
        state = self.project / ".research-state"
        graph = json.loads((state / "research_graph.json").read_text(encoding="utf-8"))
        self.assertEqual(graph["profile"], "CUMCM")
        self.assertEqual(graph["nodes"][0]["id"], "contest_intake")
        self.assertTrue((state / "competition_clock.json").exists())
        self.assertTrue((state / "competition_rules.json").exists())
        self.assertEqual(
            json.loads((state / "competition_clock.json").read_text(encoding="utf-8"))["clock_status"],
            "UNVERIFIED",
        )

    def test_research_mode_does_not_create_competition_state(self):
        research_state.init_state(self.project, "empirical", "copilot", "systems")
        state = self.project / ".research-state"
        self.assertFalse((state / "competition_clock.json").exists())
        graph = json.loads((state / "research_graph.json").read_text(encoding="utf-8"))
        self.assertEqual(graph["nodes"][0]["id"], "orientation")
```

- [ ] **Step 2: Run RED and confirm missing mode/template failures**

Run: `python -m unittest tests.test_competition_runtime.CompetitionInitializationTests -v`

Expected: FAIL because `competition` is not recognized and contest templates do not exist.

- [ ] **Step 3: Add exact contest templates and initialization branch**

```python
COMPETITION_MODES = ("competition", "competition-autopilot", "competition-review")
MODES = RESEARCH_MODES + COMPETITION_MODES
COMPETITION_TEMPLATE_DIR = ROOT / "assets" / "templates" / "competition"
COMPETITION_TEMPLATES = (
    "competition_clock.json",
    "competition_state.json",
    "competition_rules.json",
    "competition_review.json",
)

def _initialize_competition_state(state_dir: Path, created_utc: str, mode: str) -> list[str]:
    graph = _read_json(COMPETITION_TEMPLATE_DIR / "research_graph.json")
    graph.update({"skill_version": SKILL_VERSION, "created_utc": created_utc})
    _write_json(state_dir / "research_graph.json", graph)
    shutil.copy2(state_dir / "research_graph.json", state_dir / ".research-graph-initial.json")
    created = ["research_graph.json", ".research-graph-initial.json"]
    for name in COMPETITION_TEMPLATES:
        value = _read_json(COMPETITION_TEMPLATE_DIR / name)
        value.update({"skill_version": SKILL_VERSION, "created_utc": created_utc})
        if name == "competition_state.json":
            value["mode"] = mode
        _write_json(state_dir / name, value)
        created.append(name)
    return created
```

The profile must contain the seven approved reference phase intervals, three monotonically increasing safety margins, and policies for every graph node. The graph uses the 16 approved main-path node IDs and valid generic node fields.

- [ ] **Step 4: Run targeted and legacy state tests**

Run: `python -m unittest tests.test_competition_runtime.CompetitionInitializationTests tests.test_research_state tests.test_v3.V3StateTests -v`

Expected: PASS with existing research initialization unchanged.

- [ ] **Step 5: Commit Task 1**

```bash
git add assets/competition assets/templates/competition assets/schemas/competition_*.schema.json scripts/research_state.py tests/test_competition_runtime.py
git commit -m "feat: initialize CUMCM competition state"
```

---

### Task 2: Deterministic Clock and Hash-Chained Overrides

**Files:**

- Create: `scripts/competition_runtime.py`
- Modify: `tests/test_competition_runtime.py`

**Interfaces:**

- Produces: `parse_utc(value: str) -> datetime`
- Produces: `configure_clock(project: Path, start: str, deadline: str, official_source: str, actor: str, now_utc: datetime | None = None) -> dict[str, Any]`
- Produces: `verify_clock(project: Path, official_source: str, actor: str, now_utc: datetime | None = None) -> dict[str, Any]`
- Produces: `adjust_clock(project: Path, offset_seconds: int, reason: str, actor: str, now_utc: datetime | None = None) -> dict[str, Any]`
- Produces: `pause_clock(project: Path, reason: str, actor: str, now_utc: datetime | None = None) -> dict[str, Any]`
- Produces: `resume_clock(project: Path, reason: str, actor: str, now_utc: datetime | None = None) -> dict[str, Any]`
- Produces: `refresh_clock(project: Path, now_utc: datetime | None = None) -> dict[str, Any]`
- Produces: `validate_clock(project: Path) -> dict[str, Any]`

- [ ] **Step 1: Write failing clock arithmetic and validation tests**

```python
def test_clock_normalizes_offsets_and_uses_actual_duration(self):
    result = competition_runtime.configure_clock(
        self.project,
        "2026-09-10T18:00:00+08:00",
        "2026-09-13T22:00:00+08:00",
        "https://fixture.invalid/official-rules",
        "fixture-author",
        now_utc=datetime(2026, 9, 10, 12, tzinfo=timezone.utc),
    )
    clock = result["clock"]
    self.assertEqual(clock["contest_start_utc"], "2026-09-10T10:00:00Z")
    self.assertEqual(clock["submission_deadline_utc"], "2026-09-13T14:00:00Z")
    self.assertEqual(clock["contest_duration_seconds"], 76 * 3600)
    self.assertEqual(clock["elapsed_seconds"], 2 * 3600)

def test_clock_rejects_naive_and_reversed_boundaries(self):
    with self.assertRaises(competition_runtime.CompetitionError):
        competition_runtime.configure_clock(self.project, "2026-09-10T10:00:00", "2026-09-13T10:00:00Z", "source", "actor")
    with self.assertRaises(competition_runtime.CompetitionError):
        competition_runtime.configure_clock(self.project, "2026-09-13T10:00:00Z", "2026-09-10T10:00:00Z", "source", "actor")
```

- [ ] **Step 2: Run RED and confirm the runtime module is missing**

Run: `python -m unittest tests.test_competition_runtime.CompetitionClockTests -v`

Expected: FAIL because `scripts/competition_runtime.py` does not exist.

- [ ] **Step 3: Implement UTC parsing, refresh, and phase-free clock projection**

```python
def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CompetitionError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)

def _compute_times(clock: dict[str, Any], system_now: datetime) -> dict[str, Any]:
    start = parse_utc(clock["contest_start_utc"])
    deadline = parse_utc(clock["submission_deadline_utc"])
    effective = system_now + timedelta(seconds=int(clock["manual_time_offset_seconds"]))
    duration = int((deadline - start).total_seconds())
    if duration <= 0:
        raise CompetitionError("submission deadline must be after contest start")
    elapsed = int((effective - start).total_seconds())
    remaining = int((deadline - effective).total_seconds())
    return {
        "contest_duration_seconds": duration,
        "effective_now_utc": _format_utc(effective),
        "elapsed_seconds": elapsed,
        "remaining_seconds": remaining,
        "elapsed_ratio": elapsed / duration,
    }
```

- [ ] **Step 4: Write failing verification, offset, pause/resume, and tamper tests**

```python
def test_unverified_clock_cannot_be_authoritative(self):
    result = competition_runtime.configure_clock(self.project, START, DEADLINE, "", "author", now_utc=AT_HOUR_1)
    self.assertEqual(result["clock"]["clock_status"], "UNVERIFIED")
    self.assertFalse(result["clock"]["authoritative_deadline"])

def test_manual_offset_is_replayed_from_hash_chain(self):
    self.configure_verified()
    competition_runtime.adjust_clock(self.project, -1800, "official pause", "captain", now_utc=AT_HOUR_10)
    result = competition_runtime.refresh_clock(self.project, now_utc=AT_HOUR_10)
    self.assertEqual(result["clock"]["manual_time_offset_seconds"], -1800)
    events = (self.state / ".competition-clock-events.jsonl").read_text(encoding="utf-8").splitlines()
    self.assertGreaterEqual(len(events), 3)

def test_tampered_clock_event_fails_closed(self):
    self.configure_verified()
    competition_runtime.adjust_clock(self.project, 60, "clock correction", "captain", now_utc=AT_HOUR_10)
    path = self.state / ".competition-clock-events.jsonl"
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    events[-1]["reason"] = "tampered"
    path.write_text("\n".join(json.dumps(item) for item in events) + "\n", encoding="utf-8")
    with self.assertRaises(competition_runtime.CompetitionError):
        competition_runtime.refresh_clock(self.project, now_utc=AT_HOUR_10)
```

- [ ] **Step 5: Run RED for event-chain behavior**

Run: `python -m unittest tests.test_competition_runtime.CompetitionClockEventTests -v`

Expected: FAIL because event replay, hash verification, and pause/resume are absent.

- [ ] **Step 6: Implement canonical clock events and replay**

```python
def _event_hash(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def _append_clock_event(state_dir: Path, operation: str, actor: str, reason: str, old_value: Any, new_value: Any, now: datetime) -> dict[str, Any]:
    events = _load_and_verify_events(state_dir)
    event = {
        "event_id": f"CE-{len(events) + 1:04d}",
        "utc": _format_utc(now),
        "actor": actor,
        "operation": operation,
        "reason": reason,
        "old_value": old_value,
        "new_value": new_value,
        "predecessor_hash": events[-1]["event_hash"] if events else "GENESIS",
    }
    event["event_hash"] = _event_hash(event)
    with (state_dir / CLOCK_EVENT_LOG).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event
```

- [ ] **Step 7: Run all clock tests**

Run: `python -m unittest tests.test_competition_runtime.CompetitionClockTests tests.test_competition_runtime.CompetitionClockEventTests -v`

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

```bash
git add scripts/competition_runtime.py tests/test_competition_runtime.py
git commit -m "feat: add deterministic competition clock"
```

---

### Task 3: Phase Mapping, STOP RULE, HARD FREEZE, and ETA Scheduler

**Files:**

- Modify: `scripts/competition_runtime.py`
- Modify: `assets/competition/cumcm_profile.json`
- Modify: `tests/test_competition_runtime.py`

**Interfaces:**

- Produces: `phase_for(clock: dict[str, Any], profile: dict[str, Any]) -> str`
- Produces: `control_mode_for(clock: dict[str, Any]) -> str`
- Produces: `schedule(project: Path, job_estimates: dict[str, int] | None = None, critical_fix_nodes: set[str] | None = None, now_utc: datetime | None = None) -> dict[str, Any]`
- Produces: `advance(project: Path, actor: str, job_estimates: dict[str, int] | None = None, critical_fix_nodes: set[str] | None = None, now_utc: datetime | None = None) -> dict[str, Any]`
- Consumes: generic `research_graph.load_graph`, `research_graph.plan_next`, and `research_graph.transition`.

- [ ] **Step 1: Write literal-boundary phase tests**

```python
def test_default_72_hour_boundaries_and_overlays(self):
    cases = [
        (3 * 3600, "CONTEST_INTAKE_AND_SELECTION", "NORMAL", False, False),
        (10 * 3600, "MVP_MODELING", "NORMAL", False, False),
        (67 * 3600, "REVIEW_AND_REVISION", "FINALIZATION_MODE", True, False),
        (69 * 3600, "SUBMISSION_FREEZE", "FINALIZATION_MODE", True, False),
        (71 * 3600, "SUBMISSION_FREEZE", "HARD_FREEZE", True, True),
    ]
    for elapsed, phase, control, stop, hard in cases:
        clock = self.refresh_at_elapsed(elapsed)
        self.assertEqual(clock["current_phase"], phase)
        self.assertEqual(clock["control_mode"], control)
        self.assertEqual(clock["stop_rule_active"], stop)
        self.assertEqual(clock["hard_freeze_active"], hard)

def test_non_72_hour_schedule_scales_proportionally(self):
    self.configure_duration(hours=36)
    clock = competition_runtime.refresh_clock(self.project, now_utc=self.start + timedelta(hours=6))
    self.assertEqual(clock["clock"]["current_phase"], "FORMAL_MODELING")
```

- [ ] **Step 2: Run RED for missing phase computation**

Run: `python -m unittest tests.test_competition_runtime.CompetitionPhaseTests -v`

Expected: FAIL because the clock has no approved phase/control calculation.

- [ ] **Step 3: Implement proportional phases and absolute freeze overlays**

```python
def control_mode_for(clock: dict[str, Any]) -> str:
    remaining = int(clock["remaining_seconds"])
    if remaining <= 0:
        return "DEADLINE_PASSED"
    if remaining <= 2 * 3600:
        return "HARD_FREEZE"
    if remaining <= 6 * 3600:
        return "FINALIZATION_MODE"
    return "NORMAL"

def phase_for(clock: dict[str, Any], profile: dict[str, Any]) -> str:
    elapsed = int(clock["elapsed_seconds"])
    duration = int(clock["contest_duration_seconds"])
    if elapsed < 0:
        return "PRE_CONTEST"
    if elapsed >= duration:
        return "DEADLINE_PASSED"
    ratio = elapsed / duration
    for phase in profile["phases"]:
        if phase["start_ratio"] <= ratio < phase["end_ratio"]:
            return phase["id"]
    raise CompetitionError("competition profile does not cover elapsed ratio")
```

- [ ] **Step 4: Write failing scheduler and ETA tests**

```python
def test_unverified_clock_does_not_apply_time_policy(self):
    self.configure_unverified()
    result = competition_runtime.schedule(self.project, now_utc=AT_HOUR_67)
    self.assertEqual(result["status"], "CONDITIONAL")
    self.assertFalse(result["authoritative_deadline"])
    self.assertEqual(result["policy_actions"], [])

def test_eta_requires_strict_slack_after_escalating_margin(self):
    self.configure_verified()
    result = competition_runtime.schedule(
        self.project,
        job_estimates={"formal_solve": 9000},
        now_utc=AT_HOUR_69,
    )
    blocked = {item["node"]: item["reason"] for item in result["blocked"]}
    self.assertIn("formal_solve", blocked)
    self.assertIn("ETA", blocked["formal_solve"])

def test_hard_freeze_allows_only_submission_or_critical_fix(self):
    self.configure_verified()
    result = competition_runtime.schedule(
        self.project,
        job_estimates={"model_improvement": 60, "submission_preflight": 60},
        critical_fix_nodes=set(),
        now_utc=AT_HOUR_71,
    )
    self.assertNotIn("model_improvement", result["eligible"])
    self.assertIn("submission_preflight", result["eligible"])
```

- [ ] **Step 5: Run RED for policy output**

Run: `python -m unittest tests.test_competition_runtime.CompetitionSchedulerTests -v`

Expected: FAIL because `schedule` and `advance` are absent.

- [ ] **Step 6: Implement deterministic eligibility and ranking**

```python
def _rank_key(node: dict[str, Any], phase: str, control: str, graph_index: int) -> tuple[int, int, int, int]:
    affinity = 0 if phase in node.get("phase_affinity", []) else 1
    relevance = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[node.get("decision_relevance", "MEDIUM")]
    risk = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[node.get("scientific_risk", "MEDIUM")]
    if control != "NORMAL":
        risk *= 2
    return affinity, relevance, risk, graph_index

def _eta_allowed(estimated: int, remaining: int, margin: dict[str, Any]) -> bool:
    safety = max(int(margin["minimum_seconds"]), math.ceil(estimated * float(margin["eta_multiplier"])))
    return estimated + safety < remaining
```

`advance` must call `research_graph.transition` for policy changes and may only
produce `READY`, `BLOCKED`, or `REOPENED`; it cannot emit `PASS` or change
canonical evidence state.

- [ ] **Step 7: Run scheduler plus generic graph regression tests**

Run: `python -m unittest tests.test_competition_runtime.CompetitionSchedulerTests tests.test_v31_runtime.RuntimeIntegrationTests.test_graph_advance_records_conditional_feasibility_actions tests.test_v31_runtime.RuntimeIntegrationTests.test_graph_rebuild_rejects_tampered_event -v`

Expected: PASS and generic graph event-chain behavior remains intact.

- [ ] **Step 8: Commit Task 3**

```bash
git add scripts/competition_runtime.py assets/competition/cumcm_profile.json tests/test_competition_runtime.py
git commit -m "feat: schedule competition work by clock and risk"
```

---

### Task 4: Competition Method Router

**Files:**

- Create: `assets/registry/competition_method_router.json`
- Create: `assets/schemas/competition_method_router.schema.json`
- Create: `scripts/competition_method_router.py`
- Modify: `scripts/validate_registry.py`
- Modify: `tests/test_competition_runtime.py`

**Interfaces:**

- Produces: `route(task: str, explicit: str | None = None) -> dict[str, Any]`
- Produces statuses: `PASS`, `CONDITIONAL`, `UNRESOLVED`, and `FAIL`.
- Produces the nine approved output fields using snake_case JSON keys.

- [ ] **Step 1: Write failing category, baseline, ambiguity, and zero-match tests**

```python
class CompetitionMethodRouterTests(unittest.TestCase):
    def test_router_covers_required_problem_families(self):
        expected = {
            "evaluation", "prediction", "optimization", "classification-clustering",
            "graph-network", "time-series", "differential-equations", "simulation",
            "spatial-routing", "data-preparation",
        }
        self.assertEqual({item["id"] for item in competition_method_router._read()["categories"]}, expected)

    def test_small_data_prediction_starts_with_simple_baseline(self):
        result = competition_method_router.route("predict a short annual time series with 18 observations")
        self.assertEqual(result["status"], "PASS")
        self.assertIn(result["recommended_baseline"], {"linear regression", "naive forecast", "exponential smoothing"})
        self.assertNotEqual(result["recommended_primary_model"], "LSTM")

    def test_zero_match_is_unresolved_without_model_guess(self):
        result = competition_method_router.route("an underspecified contest question")
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertEqual(result["candidate_models"], [])
        self.assertIsNone(result["recommended_primary_model"])
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_competition_runtime.CompetitionMethodRouterTests -v`

Expected: FAIL because the registry and runtime do not exist.

- [ ] **Step 3: Implement a registry-driven router**

```python
def route(task: str, explicit: str | None = None) -> dict[str, Any]:
    categories = _read()["categories"]
    scored = [(len(_hits(task, item["triggers"])), item) for item in categories]
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    if not scored or scored[0][0] == 0:
        return {
            "operation": "competition-route",
            "status": "UNRESOLVED",
            "problem_type": None,
            "candidate_models": [],
            "recommended_baseline": None,
            "recommended_primary_model": None,
            "optional_improvement": None,
            "why": "insufficient problem structure",
            "main_assumptions": [],
            "failure_risks": ["model choice would be a guess"],
            "validation_plan": [],
        }
    selected = scored[0][1]
    tied = [item for score, item in scored if score == scored[0][0]]
    return _result_from_category(selected, tied, task)
```

Registry validation must require all ten categories, unique IDs, non-empty
triggers, baseline, primary candidates, assumptions, risks, validation, and a
method-class field for optimization methods (`exact`, `heuristic`, or
`metaheuristic`).

- [ ] **Step 4: Run router and registry tests**

Run: `python -m unittest tests.test_competition_runtime.CompetitionMethodRouterTests -v`

Run: `python scripts/validate_registry.py`

Expected: PASS with the academic method router unchanged.

- [ ] **Step 5: Commit Task 4**

```bash
git add assets/registry/competition_method_router.json assets/schemas/competition_method_router.schema.json scripts/competition_method_router.py scripts/validate_registry.py tests/test_competition_runtime.py
git commit -m "feat: add CUMCM modeling method router"
```

---

### Task 5: Rules, Decomposition, Assumptions, and Dashboard Contracts

**Files:**

- Modify: `scripts/competition_runtime.py`
- Modify: `assets/templates/competition/competition_state.json`
- Modify: `assets/templates/competition/competition_rules.json`
- Modify: `tests/test_competition_runtime.py`

**Interfaces:**

- Produces: `validate_competition_state(value: dict[str, Any]) -> dict[str, Any]`
- Produces: `audit_rules(project: Path) -> dict[str, Any]`
- Produces: `dashboard(project: Path, now_utc: datetime | None = None) -> dict[str, Any]`

- [ ] **Step 1: Write failing structural and rules-gate tests**

```python
def test_question_and_assumption_contracts_reject_missing_fields(self):
    state = self.read("competition_state.json")
    state["question_decomposition"] = [{"id": "Q1", "goal": "choose a site"}]
    state["assumptions"] = [{"id": "A1", "assumption": "demand is fixed"}]
    result = competition_runtime.validate_competition_state(state)
    self.assertEqual(result["status"], "FAIL")
    self.assertTrue(any("decision_variables" in item for item in result["findings"]))
    self.assertTrue(any("risk_if_violated" in item for item in result["findings"]))

def test_submission_preflight_requires_all_current_official_rules(self):
    result = competition_runtime.audit_rules(self.project)
    self.assertEqual(result["status"], "FAIL")
    self.assertEqual(
        set(result["unverified"]),
        {"contest_time", "ai_policy", "file_format", "page_limit", "submission_method", "problem_count", "discipline"},
    )
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_competition_runtime.CompetitionContractTests -v`

Expected: FAIL because the validators are absent.

- [ ] **Step 3: Implement exact required-field validation and preflight gate**

```python
QUESTION_FIELDS = (
    "id", "goal", "inputs", "decision_variables", "state_variables", "target",
    "constraints", "outputs", "required_evidence", "assumptions",
    "candidate_methods", "validation", "dependencies",
)
ASSUMPTION_FIELDS = (
    "id", "assumption", "reason", "consequence", "risk_if_violated",
    "validation_or_sensitivity", "affected_questions",
)
RULE_FIELDS = (
    "contest_time", "ai_policy", "file_format", "page_limit",
    "submission_method", "problem_count", "discipline",
)
```

Each verified rule requires `status = VERIFIED`, non-empty `official_source`,
timezone-aware `verified_utc`, and a non-empty actor. The scheduler blocks
`submission_preflight` while `audit_rules` fails.

- [ ] **Step 4: Write and run dashboard-source test**

```python
def test_dashboard_uses_refreshed_clock_and_graph_state(self):
    self.configure_verified()
    result = competition_runtime.dashboard(self.project, now_utc=AT_HOUR_31)
    self.assertEqual(result["elapsed_seconds"], 31 * 3600)
    self.assertEqual(result["remaining_seconds"], 41 * 3600)
    self.assertEqual(result["current_phase"], "VALIDATION_AND_ROBUSTNESS")
    self.assertIn("completed", result)
    self.assertIn("highest_roi_next_action", result)
    self.assertEqual(result["time_source"], "competition_runtime")
```

Run: `python -m unittest tests.test_competition_runtime.CompetitionContractTests -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add scripts/competition_runtime.py assets/templates/competition/competition_state.json assets/templates/competition/competition_rules.json tests/test_competition_runtime.py
git commit -m "feat: validate competition contracts and dashboard"
```

---

### Task 6: CUMCM Review and Score Radar

**Files:**

- Create: `scripts/competition_review.py`
- Modify: `assets/templates/competition/competition_review.json`
- Modify: `assets/schemas/competition_review.schema.json`
- Modify: `tests/test_competition_runtime.py`

**Interfaces:**

- Produces: `validate_finding(value: Any) -> dict[str, Any]`
- Produces: `audit(value_or_path: dict[str, Any] | Path) -> dict[str, Any]`
- Produces: `summary(value_or_path: dict[str, Any] | Path) -> dict[str, Any]`

- [ ] **Step 1: Write failing severity, score, and award-theater tests**

```python
def test_review_accepts_bounded_findings_and_ten_scores(self):
    value = self.valid_review()
    result = competition_review.audit(value)
    self.assertEqual(result["status"], "PASS")
    self.assertEqual(len(result["score_radar"]), 10)

def test_review_rejects_out_of_range_scores_and_award_probability(self):
    value = self.valid_review()
    value["score_radar"]["validation"] = 11
    value["largest_award_level_blocker"] = "95% chance of first prize"
    result = competition_review.audit(value)
    self.assertEqual(result["status"], "FAIL")
    self.assertTrue(any("0 through 10" in item for item in result["findings"]))
    self.assertTrue(any("award probability" in item for item in result["findings"]))
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_competition_runtime.CompetitionReviewTests -v`

Expected: FAIL because the competition review runtime does not exist.

- [ ] **Step 3: Implement exact review contracts**

```python
FINDING_FIELDS = (
    "issue", "severity", "location", "why_it_matters",
    "smallest_sufficient_fix", "estimated_scoring_impact", "evidence_anchors",
)
RADAR_FIELDS = (
    "problem_understanding", "model_appropriateness", "mathematical_rigor",
    "implementation", "validation", "innovation", "visualization", "writing",
    "reproducibility", "overall_coherence",
)
SEVERITIES = {"CRITICAL", "MAJOR", "MINOR"}
FORBIDDEN_AWARD_PATTERNS = (
    "award probability", "chance of first prize", "guaranteed prize",
    "获奖概率", "稳拿", "保送一等奖",
)
```

The audit orders findings CRITICAL, MAJOR, MINOR without altering the source
objects and returns the four required summary fields.

- [ ] **Step 4: Run review tests**

Run: `python -m unittest tests.test_competition_runtime.CompetitionReviewTests -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

```bash
git add scripts/competition_review.py assets/templates/competition/competition_review.json assets/schemas/competition_review.schema.json tests/test_competition_runtime.py
git commit -m "feat: add CUMCM competition review rubric"
```

---

### Task 7: Skill Routing, CUMCM Reference, and Behavior Cases

**Files:**

- Create: `references/competitions/cumcm.md`
- Modify: `SKILL.md`
- Modify: `assets/evals/behavior_cases.json`
- Modify: `tests/test_behavior_cases.py`
- Modify: `tests/test_competition_runtime.py`

**Interfaces:**

- Produces progressive-disclosure routing from each competition mode to the
  CUMCM reference and deterministic scripts.
- Produces behavior cases `CUMCM-CLOCK-AUTHORITY`,
  `CUMCM-COMPLEXITY-PRESSURE`, and `CUMCM-HARD-FREEZE-PRESSURE`.

- [ ] **Step 1: Add failing application-level behavior-case tests before editing the Skill**

```python
def test_cumcm_pressure_cases_cover_clock_model_and_freeze_failures(self):
    by_id = {case["id"]: case for case in self.value["cases"]}
    self.assertEqual(
        {"CUMCM-CLOCK-AUTHORITY", "CUMCM-COMPLEXITY-PRESSURE", "CUMCM-HARD-FREEZE-PRESSURE"} <= set(by_id),
        True,
    )
    self.assertIn("uses runtime-computed remaining time", by_id["CUMCM-CLOCK-AUTHORITY"]["required_behaviors"])
    self.assertIn("estimates the remaining job runtime and safety margin", by_id["CUMCM-HARD-FREEZE-PRESSURE"]["required_behaviors"])
    self.assertIn("guesses the remaining time", by_id["CUMCM-CLOCK-AUTHORITY"]["forbidden_behaviors"])
```

- [ ] **Step 2: Run RED and record the baseline gap**

Run: `python -m unittest tests.test_behavior_cases.BehaviorCaseTests.test_cumcm_pressure_cases_cover_clock_model_and_freeze_failures -v`

Expected: FAIL because no CUMCM behavior cases exist. Record this deterministic
baseline as the no-guidance control; multi-agent sampling is unavailable and
must not be simulated or misreported as a model evaluation.

- [ ] **Step 3: Add the three complete behavior cases**

Each case must include non-empty `prompt`, `departments`,
`required_behaviors`, `forbidden_behaviors`, and `required_artifacts`. The
clock case forbids LLM time arithmetic; the model-pressure case forbids adding
neural networks or metaheuristics for appearance; the freeze case forbids new
scientific direction and unsafe ETA.

- [ ] **Step 4: Add the progressive CUMCM reference and compact SKILL routing**

`SKILL.md` adds only:

```markdown
| `competition` | Active CUMCM work with author-owned major direction changes | runtime dashboard and highest-ROI eligible action |
| `competition-autopilot` | Compare supplied contest problems and start a defensible baseline | structured problem comparison and clock-aware plan |
| `competition-review` | Red-team a contest paper and submission package | severity-ordered findings and score radar |
```

The routing section directs competition modes to
`references/competitions/cumcm.md`, `scripts/competition_runtime.py`,
`scripts/competition_method_router.py`, and `scripts/competition_review.py`.
The reference contains the approved 72-hour workflow, model-selection rule,
question and assumption contracts, provenance boundaries, validation choices,
summary/figure priorities, official-rule verification, STOP RULE, HARD FREEZE,
and the three invocation examples. It does not contain current-year rule facts.

- [ ] **Step 5: Run behavior and runtime routing tests**

Run: `python -m unittest tests.test_behavior_cases tests.test_competition_runtime -v`

Expected: PASS. Report the cases as deterministic harness coverage, not
model-backed behavior evaluation.

- [ ] **Step 6: Commit Task 7**

```bash
git add SKILL.md references/competitions/cumcm.md assets/evals/behavior_cases.json tests/test_behavior_cases.py tests/test_competition_runtime.py
git commit -m "docs: route CUMCM competition workflows"
```

---

### Task 8: Synthetic Competition E2E

**Files:**

- Create: `assets/fixtures/cumcm/synthetic_problem.json`
- Create: `scripts/competition_smoke_run.py`
- Create: `tests/test_competition_e2e.py`

**Interfaces:**

- Produces: `competition_smoke_run.run(output: Path | None = None) -> dict[str, Any]`
- Uses fixed injected test times but the production CLI system clock.
- Reports `evaluation_class = HARNESS_SELF_TEST` and
  `model_behavior = NOT_RUN; deterministic harness only`.

- [ ] **Step 1: Write failing E2E test**

```python
class CompetitionE2ETests(unittest.TestCase):
    def test_synthetic_fixture_runs_through_clock_router_graph_and_provenance(self):
        result = competition_smoke_run.run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["competition"], "CUMCM")
        self.assertEqual(result["evaluation_class"], "HARNESS_SELF_TEST")
        self.assertIn("NOT_RUN", result["model_behavior"])
        self.assertEqual(result["baseline"]["method"], "exhaustive enumeration")
        self.assertEqual(result["baseline"]["selected_site"], "B")
        self.assertEqual(result["execution"]["exit_status"], 0)
        self.assertTrue(result["execution"]["output_sha256"].startswith("sha256:"))
        self.assertEqual(result["clock_checks"]["hard_freeze"], "HARD_FREEZE")
        self.assertEqual(result["graph_validation"], "PASS")
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_competition_e2e -v`

Expected: FAIL because the fixture and runner do not exist.

- [ ] **Step 3: Add a hand-checkable facility fixture**

```json
{
  "id": "SYNTHETIC-CUMCM-FACILITY-001",
  "question": "Choose one facility with capacity at least 80 and minimum declared cost.",
  "sites": [
    {"id": "A", "capacity": 70, "cost": 8},
    {"id": "B", "capacity": 90, "cost": 11},
    {"id": "C", "capacity": 100, "cost": 14}
  ],
  "minimum_capacity": 80,
  "expected_selected_site": "B"
}
```

- [ ] **Step 4: Implement E2E using real local files and canonical evidence helpers**

```python
def solve_fixture(value: dict[str, Any]) -> dict[str, Any]:
    feasible = [site for site in value["sites"] if site["capacity"] >= value["minimum_capacity"]]
    selected = min(feasible, key=lambda site: (site["cost"], site["id"]))
    return {"method": "exhaustive enumeration", "selected_site": selected["id"], "cost": selected["cost"]}
```

The runner creates a temporary competition project, writes input/config/code,
executes a subprocess command, records stdout/stderr and hashes, anchors the
result with `evidence_anchor`, transitions only graph nodes with real fixture
artifacts, validates the graph event chain, and probes normal/finalization/hard
freeze schedules through injected times.

- [ ] **Step 5: Run E2E and original smoke regression**

Run: `python -m unittest tests.test_competition_e2e -v`

Run: `python scripts/competition_smoke_run.py --output .competition-smoke-result.json`

Run: `python scripts/smoke_run.py --output .ci-smoke-result.json`

Expected: all three commands exit 0; both smoke artifacts distinguish harness
self-tests from model-backed evaluation.

- [ ] **Step 6: Remove generated root smoke outputs after inspection**

Use PowerShell `Remove-Item -LiteralPath '.competition-smoke-result.json','.ci-smoke-result.json'` only after resolving each path inside the repository root. These are reproducible generated artifacts and are not committed.

- [ ] **Step 7: Commit Task 8**

```bash
git add assets/fixtures/cumcm/synthetic_problem.json scripts/competition_smoke_run.py tests/test_competition_e2e.py
git commit -m "test: add synthetic CUMCM end-to-end fixture"
```

---

### Task 9: CLI, Documentation, Validation, and CI Integration

**Files:**

- Modify: `scripts/competition_runtime.py`
- Modify: `scripts/competition_method_router.py`
- Modify: `scripts/competition_review.py`
- Modify: `scripts/validate_release.py`
- Modify: `scripts/build_manifest.py`
- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_competition_runtime.py`
- Modify: `tests/test_v311_final_consistency.py`

**Interfaces:**

- Produces machine-readable CLIs with exit 0 for PASS, exit 1 for bounded
  validation failures/UNRESOLVED routing, and exit 2 for malformed operations.
- Adds CI command `python scripts/competition_smoke_run.py --output .competition-smoke-result.json`.

- [ ] **Step 1: Write failing CLI and CI contract tests**

```python
def test_runtime_status_cli_returns_runtime_computed_dashboard(self):
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "competition_runtime.py"), "status", str(self.project)],
        text=True,
        capture_output=True,
        check=False,
    )
    self.assertEqual(completed.returncode, 0)
    value = json.loads(completed.stdout)
    self.assertEqual(value["dashboard"]["time_source"], "competition_runtime")

def test_ci_runs_competition_smoke_and_uploads_its_hidden_artifact(self):
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    self.assertIn("python scripts/competition_smoke_run.py --output .competition-smoke-result.json", workflow)
    self.assertIn(".competition-smoke-result.json", workflow)
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_competition_runtime.CompetitionCliTests tests.test_v311_final_consistency.FinalConsistencyRegressionTests.test_ci_runs_competition_smoke_and_uploads_its_hidden_artifact -v`

Expected: FAIL because CLI dispatch and CI integration are incomplete.

- [ ] **Step 3: Complete argparse surfaces and CI artifact upload**

```python
def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _dispatch(args)
    except CompetitionError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1
```

`validate_release.py` maps every new competition schema to its matching
competition template or registry document. `build_manifest.py` adds
`.competition-smoke-result.json` to `EXCLUDED_FILES` so a generated smoke
result can never become release-controlled source.

CI uploads `.competition-smoke-result.json` beside the existing runtime
artifacts with `include-hidden-files: true` and `if-no-files-found: error`.

- [ ] **Step 4: Add English and Chinese usage sections**

Both READMEs document the three modes, clock configuration and verification,
automatic dashboard, method routing, competition review, synthetic harness
boundary, and the three invocation examples. They state that current official
rules must be verified and that no award outcome is predicted.

- [ ] **Step 5: Run CLI, consistency, privacy, and validation tests**

Run: `python -m unittest tests.test_competition_runtime.CompetitionCliTests tests.test_v311_final_consistency -v`

Run: `python scripts/validate_registry.py`

Run: `python scripts/privacy_lint.py`

Expected: all commands exit 0.

- [ ] **Step 6: Commit Task 9**

```bash
git add scripts/competition_runtime.py scripts/competition_method_router.py scripts/competition_review.py scripts/validate_release.py scripts/build_manifest.py README.md README_zh.md .github/workflows/ci.yml tests/test_competition_runtime.py tests/test_v311_final_consistency.py
git commit -m "docs: integrate CUMCM runtime and CI usage"
```

---

### Task 10: Manifest Refresh and Full Verification

**Files:**

- Modify: `SHA256SUMS.txt`

**Interfaces:**

- Produces repository manifests generated by the existing deterministic tool.
- Does not produce or edit a Git tag or GitHub Release.

- [ ] **Step 1: Run manifest check to observe expected RED**

Run: `python scripts/build_manifest.py --check`

Expected: FAIL listing new or changed repository artifacts until manifests are refreshed.

- [ ] **Step 2: Regenerate the checksum manifest using the existing write mode**

Run: `python scripts/build_manifest.py`

Expected: exit 0 and `SHA256SUMS.txt` is rewritten with canonical LF-normalized hashes. Do not hand-edit checksums or change `release_manifest.json`.

- [ ] **Step 3: Re-run manifest and release validation**

Run: `python scripts/build_manifest.py --check`

Run: `python scripts/validate_release.py`

Expected: both exit 0.

- [ ] **Step 4: Run the complete unit and integration suite**

Run: `python -m unittest discover -s tests -p 'test*.py' -v`

Expected: all prior 57 and all new tests pass with zero failures/errors.

- [ ] **Step 5: Run all deterministic repository gates**

Run: `python scripts/validate_registry.py`

Run: `python scripts/privacy_lint.py`

Run: `python scripts/security_pressure_run.py --output .security-pressure-run`

Run: `python scripts/smoke_run.py --output .ci-smoke-result.json`

Run: `python scripts/check_smoke.py .ci-smoke-result.json`

Run: `python scripts/competition_smoke_run.py --output .competition-smoke-result.json`

Expected: every command exits 0. The original and competition smoke outputs
state model-backed behavior evaluation is `NOT_RUN`.

- [ ] **Step 6: Inspect generated artifacts, then remove only disposable outputs**

Resolve `.security-pressure-run`, `.ci-smoke-result.json`, and
`.competition-smoke-result.json` inside the repository. Remove those generated
paths using native PowerShell literal paths. Do not remove committed benchmark,
manifest, source, or fixture files.

- [ ] **Step 7: Run final integrity checks after cleanup**

Run: `git diff --check`

Run: `python scripts/build_manifest.py --check`

Run: `python scripts/validate_release.py`

Run: `git status --short`

Expected: no whitespace errors, both validators exit 0, and status contains
only the intended implementation files.

- [ ] **Step 8: Commit generated manifests and any final verified fixes**

```bash
git add SHA256SUMS.txt
git commit -m "chore: refresh CUMCM profile manifests"
```

- [ ] **Step 9: Record final branch evidence without pushing or releasing**

Run: `git rev-parse HEAD`

Run: `git diff --stat origin/main...HEAD`

Run: `git log --oneline origin/main..HEAD`

Report the branch, final SHA, file changes, new modes/categories/tests, old
regression count, E2E status, remaining CRITICAL/MAJOR findings, and merge
recommendation. Do not merge, tag, release, or publish automatically.
