"""Local sequential pipeline driver."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Mapping

from ..processes import pipeline as pipeline_process


def _load_out(run_dir: Path) -> dict[str, Any] | None:
    out_path = run_dir / "out.json"
    if not out_path.exists():
        return None
    return pipeline_process._load_json(out_path)


def _status_from_out(out: Mapping[str, Any] | None) -> str:
    if not out:
        return "failed"
    status = pipeline_process._normalize_str(out.get("status"))
    if status in ("skipped", "failed"):
        return status
    return "success"


def run_local_sequential(
    cfg: Any,
    grid_run_id: str,
    *,
    clearml_enabled: bool,
    plan: Mapping[str, Any] | None = None,
    parent_task_id: str | None = None,
) -> dict[str, Any]:
    if plan is None:
        raise ValueError("plan is required for local pipeline driver.")
    limit_violations = pipeline_process._collect_limit_violations(cfg, plan)
    limit_exceeded = bool(limit_violations and not plan["plan_only"])
    if plan["plan_only"]:
        print(pipeline_process._format_plan_summary(cfg, plan))
        if limit_violations:
            report = pipeline_process._format_limit_violation_report(limit_violations)
            if report:
                print(report, file=sys.stderr)
    elif limit_exceeded:
        report = pipeline_process._format_limit_violation_report(limit_violations)
        if report:
            print(report, file=sys.stderr)
    repo_root = pipeline_process._resolve_repo_root()
    config_dir = repo_root / "conf"
    run_overrides = dict(plan["run_overrides"])
    if parent_task_id:
        run_overrides["run.clearml.parent_task_id"] = parent_task_id
    data_overrides = dict(plan["data_overrides"])
    downstream_data_overrides = dict(plan["downstream_data_overrides"])
    eval_overrides = plan["eval_overrides"]
    steps = plan["steps"]

    dataset_register_ref: dict[str, Any] | None = None
    preprocess_refs: list[dict[str, Any]] = []
    train_refs: list[dict[str, Any]] = []
    ensemble_refs: list[dict[str, Any]] = []
    leaderboard_ref: dict[str, Any] | None = None
    infer_ref: dict[str, Any] | None = None

    fail_policy = pipeline_process._resolve_fail_policy(cfg)
    allow_skipped = bool(fail_policy.get("allow_skipped"))
    allowed_failures = int(fail_policy.get("allowed_failures", 0))
    fail_fast = bool(fail_policy.get("fail_fast"))

    executed_jobs = 0
    leaderboard_out: dict[str, Any] | None = None
    fail_fast_triggered = False
    fail_fast_index: int | None = None

    def _run_step(args: list[str], run_dir: Path) -> tuple[str, dict[str, Any] | None, str | None, str | None]:
        error = None
        try:
            pipeline_process._run_cli_task(args, cwd=repo_root, config_dir=config_dir)
        except Exception as exc:
            error = str(exc)
        out = _load_out(run_dir)
        status = _status_from_out(out)
        if error and status != "failed":
            status = "failed"
        reason = pipeline_process._normalize_str(out.get("reason")) if out else None
        return status, out, reason, error

    if not plan["plan_only"] and not limit_exceeded:
        preprocess_outputs: dict[str, dict[str, Any]] = {}
        if plan["run_preprocess"]:
            for step in steps["preprocess"]:
                preprocess_variant = step.get("preprocess_variant")
                overrides = pipeline_process._merge_overrides(
                    run_overrides, downstream_data_overrides, step["overrides"]
                )
                args = ["task=preprocess", *pipeline_process._overrides_to_args(overrides)]
                status, out, reason, error = _run_step(args, step["run_dir"])
                preprocess_refs.append(
                    pipeline_process._build_ref(
                        run_dir=step["run_dir"],
                        preprocess_variant=preprocess_variant,
                        processed_dataset_id=(out or {}).get("processed_dataset_id"),
                        split_hash=(out or {}).get("split_hash"),
                        recipe_hash=(out or {}).get("recipe_hash"),
                        status=status,
                        reason=reason,
                        error=error,
                    )
                )
                preprocess_outputs[str(preprocess_variant)] = {
                    "run_dir": step["run_dir"],
                    "out": out,
                    "status": status,
                    "reason": reason,
                    "error": error,
                }

        train_success = 0
        train_failed = 0
        train_skipped = 0
        if plan["run_train"]:
            for idx, step in enumerate(steps["train"]):
                preprocess_variant = step.get("preprocess_variant")
                payload = preprocess_outputs.get(str(preprocess_variant))
                preprocess_out = payload.get("out") if payload else None
                processed_dataset_id = None
                if preprocess_out:
                    processed_dataset_id = pipeline_process._normalize_str(
                        preprocess_out.get("processed_dataset_id")
                    )
                overrides = pipeline_process._merge_overrides(
                    run_overrides,
                    downstream_data_overrides,
                    eval_overrides,
                    step["overrides"],
                )
                if processed_dataset_id:
                    overrides["data.processed_dataset_id"] = processed_dataset_id
                args = ["task=train_model", *pipeline_process._overrides_to_args(overrides)]
                status, out, reason, error = _run_step(args, step["run_dir"])
                executed_jobs += 1
                if status == "success":
                    train_success += 1
                elif status == "skipped":
                    train_skipped += 1
                else:
                    train_failed += 1
                train_refs.append(
                    pipeline_process._build_ref(
                        run_dir=step["run_dir"],
                        preprocess_variant=preprocess_variant,
                        model_variant=step.get("model_variant"),
                        train_task_id=(out or {}).get("train_task_id"),
                        model_id=(out or {}).get("model_id"),
                        best_score=(out or {}).get("best_score"),
                        primary_metric=(out or {}).get("primary_metric"),
                        hpo_run_id=step.get("hpo_run_id"),
                        hpo_params=step.get("hpo_params"),
                        status=status,
                        reason=reason,
                        error=error,
                    )
                )
                effective_failures = train_failed
                if not allow_skipped:
                    effective_failures += train_skipped
                if fail_fast and effective_failures > allowed_failures:
                    fail_fast_triggered = True
                    fail_fast_index = idx
                    break
        if fail_fast_triggered and fail_fast_index is not None:
            for step in steps["train"][fail_fast_index + 1 :]:
                train_refs.append(
                    pipeline_process._build_ref(
                        run_dir=step["run_dir"],
                        preprocess_variant=step.get("preprocess_variant"),
                        model_variant=step.get("model_variant"),
                        hpo_run_id=step.get("hpo_run_id"),
                        hpo_params=step.get("hpo_params"),
                        status="skipped",
                        reason="fail_fast",
                    )
                )

        if plan.get("run_ensemble"):
            if fail_fast_triggered:
                for step in steps["ensemble"]:
                    ensemble_refs.append(
                        pipeline_process._build_ref(
                            run_dir=step["run_dir"],
                            preprocess_variant=step.get("preprocess_variant"),
                            model_variant="ensemble_mean_topk",
                            status="skipped",
                            reason="fail_fast",
                        )
                    )
            else:
                for step in steps["ensemble"]:
                    preprocess_variant = step.get("preprocess_variant")
                    payload = preprocess_outputs.get(str(preprocess_variant))
                    processed_dataset_id = None
                    if payload is not None and payload.get("out"):
                        processed_dataset_id = pipeline_process._normalize_str(
                            payload["out"].get("processed_dataset_id")
                        )
                    overrides = pipeline_process._merge_overrides(
                        run_overrides,
                        eval_overrides,
                        step["overrides"],
                    )
                    if processed_dataset_id:
                        overrides["data.processed_dataset_id"] = processed_dataset_id
                    args = ["task=train_ensemble", *pipeline_process._overrides_to_args(overrides)]
                    status, out, reason, error = _run_step(args, step["run_dir"])
                    ensemble_refs.append(
                        pipeline_process._build_ref(
                            run_dir=step["run_dir"],
                            preprocess_variant=preprocess_variant,
                            train_task_id=(out or {}).get("train_task_id"),
                            model_id=(out or {}).get("model_id"),
                            best_score=(out or {}).get("best_score"),
                            primary_metric=(out or {}).get("primary_metric"),
                            model_variant="ensemble_mean_topk",
                            status=status,
                            reason=reason,
                            error=error,
                        )
                    )

        if plan["run_leaderboard"]:
            step = steps["leaderboard"]
            if step is None:
                raise ValueError("leaderboard step is missing.")
            if fail_fast_triggered:
                leaderboard_ref = pipeline_process._build_ref(
                    run_dir=step["run_dir"], status="skipped", reason="fail_fast"
                )
            else:
                all_train_refs = [
                    ref for ref in [*train_refs, *ensemble_refs] if ref.get("status") == "success"
                ]
                if not all_train_refs:
                    leaderboard_ref = pipeline_process._build_ref(
                        run_dir=step["run_dir"], status="skipped", reason="no_successful_train"
                    )
                else:
                    overrides = pipeline_process._merge_overrides(
                        run_overrides, eval_overrides, step["overrides"]
                    )
                    if clearml_enabled:
                        train_task_ids = [
                            ref.get("train_task_id") or ref.get("task_id")
                            for ref in all_train_refs
                            if ref.get("train_task_id") or ref.get("task_id")
                        ]
                        if not train_task_ids:
                            leaderboard_ref = pipeline_process._build_ref(
                                run_dir=step["run_dir"],
                                status="skipped",
                                reason="missing_train_task_id",
                            )
                        else:
                            overrides["leaderboard.train_task_ids"] = train_task_ids
                            args = ["task=leaderboard", *pipeline_process._overrides_to_args(overrides)]
                            status, out, reason, error = _run_step(args, step["run_dir"])
                            if out and status == "success":
                                leaderboard_out = out
                            leaderboard_ref = pipeline_process._build_ref(
                                run_dir=step["run_dir"],
                                status=status,
                                reason=reason,
                                error=error,
                            )
                    else:
                        train_run_dirs = [
                            ref.get("run_dir") for ref in all_train_refs if ref.get("run_dir")
                        ]
                        if not train_run_dirs:
                            leaderboard_ref = pipeline_process._build_ref(
                                run_dir=step["run_dir"],
                                status="skipped",
                                reason="missing_train_run_dir",
                            )
                        else:
                            overrides["leaderboard.train_run_dirs"] = train_run_dirs
                            args = ["task=leaderboard", *pipeline_process._overrides_to_args(overrides)]
                            status, out, reason, error = _run_step(args, step["run_dir"])
                            if out and status == "success":
                                leaderboard_out = out
                            leaderboard_ref = pipeline_process._build_ref(
                                run_dir=step["run_dir"],
                                status=status,
                                reason=reason,
                                error=error,
                            )

        if plan["run_infer"]:
            step = steps["infer"]
            if step is None:
                raise ValueError("infer step is missing.")
            if fail_fast_triggered:
                infer_ref = pipeline_process._build_ref(
                    run_dir=step["run_dir"], status="skipped", reason="fail_fast"
                )
            elif leaderboard_out is None:
                infer_ref = pipeline_process._build_ref(
                    run_dir=step["run_dir"], status="skipped", reason="leaderboard_missing"
                )
            else:
                infer_cfg = getattr(cfg, "infer", None)
                overrides = pipeline_process._merge_overrides(run_overrides, step["overrides"])
                if clearml_enabled:
                    train_task_id = pipeline_process._normalize_str(
                        leaderboard_out.get("recommended_train_task_id")
                    )
                    train_task_id = train_task_id or pipeline_process._normalize_str(
                        getattr(infer_cfg, "train_task_id", None)
                    )
                    model_id = pipeline_process._normalize_str(getattr(infer_cfg, "model_id", None))
                    if train_task_id:
                        overrides["infer.train_task_id"] = train_task_id
                    elif model_id:
                        overrides["infer.model_id"] = model_id
                    else:
                        infer_ref = pipeline_process._build_ref(
                            run_dir=step["run_dir"],
                            status="skipped",
                            reason="missing_recommendation",
                        )
                        overrides = None
                else:
                    model_id = pipeline_process._normalize_str(
                        leaderboard_out.get("recommended_model_id")
                    )
                    train_task_ref = pipeline_process._normalize_str(
                        leaderboard_out.get("recommended_train_task_ref")
                    )
                    if model_id:
                        overrides["infer.model_id"] = model_id
                    elif train_task_ref:
                        overrides["infer.train_task_id"] = train_task_ref
                    else:
                        fallback_model = pipeline_process._normalize_str(
                            getattr(infer_cfg, "model_id", None)
                        )
                        fallback_task = pipeline_process._normalize_str(
                            getattr(infer_cfg, "train_task_id", None)
                        )
                        if fallback_model:
                            overrides["infer.model_id"] = fallback_model
                        elif fallback_task:
                            overrides["infer.train_task_id"] = fallback_task
                        else:
                            infer_ref = pipeline_process._build_ref(
                                run_dir=step["run_dir"],
                                status="skipped",
                                reason="missing_recommendation",
                            )
                            overrides = None
                if overrides is not None:
                    args = ["task=infer", *pipeline_process._overrides_to_args(overrides)]
                    status, out, reason, error = _run_step(args, step["run_dir"])
                    infer_ref = pipeline_process._build_ref(
                        run_dir=step["run_dir"],
                        status=status,
                        reason=reason,
                        error=error,
                    )

    plan_payload = pipeline_process._serialize_pipeline_plan(plan)
    pipeline_run = {
        "grid_run_id": grid_run_id,
        "plan_only": plan["plan_only"],
        "planned_jobs": int(plan["plan_info"].get("planned_jobs", 0)),
        "executed_jobs": int(executed_jobs),
        "skipped_due_to_policy": int(plan["plan_info"].get("skipped_due_to_policy", 0)),
        "limit_exceeded": limit_exceeded,
        "limit_violations": limit_violations or None,
        "plan": plan_payload,
        "dataset_register_ref": dataset_register_ref,
        "preprocess_ref": preprocess_refs,
        "train_refs": train_refs,
        "ensemble_refs": ensemble_refs,
        "leaderboard_ref": leaderboard_ref,
        "infer_ref": infer_ref,
        "grid": {
            "preprocess_variants": plan["preprocess_variants"],
            "model_variants": plan["model_variants"],
            "max_jobs": plan["max_jobs"],
            "max_hpo_trials": plan["max_hpo_trials"],
            "hpo": {
                "enabled": plan["hpo_enabled"],
                "params": plan["hpo_params_cfg"],
            },
        },
        "policy": {
            "limits": dict(plan["limits"]),
            "pipeline_limits": dict(plan.get("pipeline_limits") or {}),
            "parallelism": dict(plan.get("parallelism") or {}),
            "selection": pipeline_process._resolve_exec_policy_selection(cfg),
            "fail_policy": dict(fail_policy),
        },
    }
    return pipeline_run
