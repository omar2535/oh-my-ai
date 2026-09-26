"""`omai up`: diff desired state against the machine, then apply steps in order."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from omai import auth, install, skills
from omai.context import Ctx
from omai.detect import detect, unmet_requirements
from omai.install import Outcome


@dataclass
class Step:
    id: str
    description: str
    run: Callable[[], Outcome]
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Plan:
    steps: list[Step] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class StepResult:
    step: Step
    status: str  # ok | failed | skipped
    message: str


@dataclass
class Summary:
    results: list[StepResult]
    notes: list[str]

    @property
    def failed(self) -> list[StepResult]:
        return [r for r in self.results if r.status != "ok"]

    @property
    def ok(self) -> bool:
        return not self.failed


def plan(ctx: Ctx, only: list[str] | None = None, with_login: bool = True) -> Plan:
    result = Plan()
    harnesses = [h for h in ctx.managed() if not only or h.id in only]
    runtime_steps: dict[str, Step] = {}
    installs, patches, logins = [], [], []
    for harness in harnesses:
        found = detect(harness)
        planned_install = None
        if found is not None:
            ctx.state.installs[harness.id] = found.to_state()
            result.notes += [f"{harness.id}: {w}" for w in found.warnings]
        else:
            channel = install.choose_channel(harness, ctx.config.harnesses[harness.id].channel)
            deps = []
            for req, have in unmet_requirements(channel):
                if req.runtime in install.RUNTIME_INSTALLERS:
                    step_id = f"runtime:{req.runtime}"
                    runtime_steps.setdefault(
                        step_id,
                        Step(step_id, f"install {req.runtime} (user-local)", lambda r=req: install.ensure_runtime(r)),
                    )
                    deps.append(step_id)
                else:
                    result.notes.append(f"{harness.id}: {install.runtime_hint(req, have)}")
            planned_install = f"install:{harness.id}"
            installs.append(
                Step(
                    planned_install,
                    f"install {harness.name} via {channel.id}",
                    lambda h=harness, c=channel: install.install(ctx, h, c),
                    deps,
                )
            )
        result.notes += [f"{harness.id}: {hint}" for hint in install.system_prereq_hints(harness, ctx.os_kind)]
        if found is not None and not found.on_path:
            continue  # runtime-bound off PATH: never reinstall, never probe
        deps = [planned_install] if planned_install else []

        pending = harness.config_patches if planned_install else install.pending_patches(ctx, harness)
        for patch in pending:
            patches.append(
                Step(
                    f"configure:{harness.id}:{patch.key}",
                    f"set {harness.name} {patch.key} = {patch.value}",
                    lambda h=harness, p=patch: install.config_set(ctx, h, p.key, p.value),
                    deps,
                )
            )
        if not with_login or harness.login.mode == "none":
            continue
        if harness.login.mode == "manual":
            if found is not None and auth.auth_status(ctx, harness) != auth.OK:
                result.notes.append(f"{harness.id}: not logged in — {auth.manual_hint(ctx, harness)}")
            continue
        if planned_install or auth.auth_status(ctx, harness) != auth.OK:
            logins.append(
                Step(
                    f"login:{harness.id}",
                    f"log in to {harness.name}",
                    lambda h=harness: _login_outcome(ctx, h),
                    deps,
                )
            )
    ctx.state.save()
    skill_step = _skills_step(ctx, installs)
    result.steps = [*runtime_steps.values(), *installs, *patches, *skill_step, *logins]
    return result


def _skills_step(ctx: Ctx, installs: list[Step]) -> list[Step]:
    actions = skills.plan(ctx)
    external_pending = any(
        s.id == f"install:{h.id}" for s in installs for h in ctx.managed() if h.skills_dir.kind == "external_dirs"
    )
    if not actions and not external_pending:
        return []
    names = sorted({a.name for a in actions if a.kind != "conflict"})
    desc = f"sync skills ({', '.join(names) or 'harness wiring'})"

    def run() -> Outcome:
        results = skills.sync(ctx)
        failed = [f"{a.name}: {o.message}" for a, o in results if not o.ok]
        return Outcome(not failed, "; ".join(failed) or f"{len(results)} change(s)")

    return [Step("skills:sync", desc, run)]


def _login_outcome(ctx: Ctx, harness) -> Outcome:
    result = auth.login(ctx, harness)
    return Outcome(result.ok, result.message)


def execute(p: Plan, on_step: Callable[[Step], None] | None = None) -> Summary:
    """Run every step; failures don't stop others, dependents of failures are skipped."""
    results: list[StepResult] = []
    failed: set[str] = set()
    for step in p.steps:
        blocked = [d for d in step.depends_on if d in failed]
        if blocked:
            failed.add(step.id)
            results.append(StepResult(step, "skipped", f"skipped: {', '.join(blocked)} failed"))
            continue
        if on_step:
            on_step(step)
        try:
            outcome = step.run()
        except Exception as exc:  # one broken step must not abort the whole run
            outcome = Outcome(False, f"{type(exc).__name__}: {exc}")
        if not outcome.ok:
            failed.add(step.id)
        results.append(StepResult(step, "ok" if outcome.ok else "failed", outcome.message))
    return Summary(results, p.notes)
