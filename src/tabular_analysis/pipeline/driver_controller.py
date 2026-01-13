"""PipelineController driver (template clone)."""

from __future__ import annotations

import inspect
from typing import Any

from ..clearml.templates import resolve_template_task_id
from ..platform_adapter import (
    apply_clearml_task_overrides,
    apply_pipeline_parallelism,
    create_pipeline_controller_from_template,
    pipeline_require_clearml_agent,
    pipeline_step_task_id_ref,
)
from ..processes import pipeline as pipeline_process
import sys


def _collect_step_task_ids(controller: Any) -> dict[str, str]:
    getter = getattr(controller, "get_processed_nodes", None)
    nodes = getter() if callable(getter) else {}
    payload: dict[str, str] = {}
    for name, node in dict(nodes).items():
        task_id = getattr(node, "executed", None)
        if not task_id and getattr(node, "job", None):
            job = node.job
            if hasattr(job, "task_id"):
                task_id = job.task_id() if callable(job.task_id) else job.task_id
        if task_id:
            payload[str(name)] = str(task_id)
    return payload


def _add_pipeline_step(
    controller: Any,
    *,
    execution_queue: str | None = None,
    **kwargs: Any,
) -> None:
    add_step = getattr(controller, "add_step", None)
    if not callable(add_step):
        raise AttributeError("Pipeline controller does not support add_step.")
    if execution_queue:
        try:
            signature = inspect.signature(add_step)
        except Exception:
            signature = None
        if signature is not None and "execution_queue" in signature.parameters:
            kwargs["execution_queue"] = execution_queue
    add_step(**kwargs)


def _resolve_template_task_ids(cfg: Any, plan: dict[str, Any]) -> dict[str, str]:
    required: set[str] = set()
    if plan.get("run_preprocess") or plan.get("run_train"):
        required.add("preprocess")
    if plan.get("run_train"):
        required.add("train_model")
    if plan.get("run_ensemble"):
        required.add("train_ensemble")
    if plan.get("run_leaderboard"):
        required.add("leaderboard")
    if plan.get("run_infer"):
        required.add("infer")
    template_task_ids: dict[str, str] = {}
    for task_name in sorted(required):
        template_task_ids[task_name] = resolve_template_task_id(cfg, task_name)
    return template_task_ids


def run_pipeline_controller(
    cfg: Any,
    grid_run_id: str,
    *,
    controller_execution: str | None = None,
    plan: dict[str, Any] | None = None,
    controller: Any | None = None,
    parent_task_id: str | None = None,
) -> dict[str, Any]:
    controller_execution = pipeline_process._normalize_str(controller_execution) or ""
    run_controller_locally = controller_execution != "pipeline_controller"
    if plan is None:
        raise ValueError("plan is required for pipeline controller driver.")
    parallelism = pipeline_process._resolve_pipeline_parallelism(cfg)
    limit_violations = pipeline_process._collect_limit_violations(cfg, plan)
    limit_exceeded = bool(limit_violations and not plan["plan_only"])
    if plan["plan_only"]:
        pipeline_process._apply_parallelism_dependencies(
            plan,
            max_concurrent_steps=parallelism["max_concurrent_steps"],
            max_concurrent_train=parallelism["max_concurrent_train"],
        )
        print(pipeline_process._format_plan_summary(cfg, plan))
        if limit_violations:
            report = pipeline_process._format_limit_violation_report(limit_violations)
            if report:
                print(report, file=sys.stderr)
    elif limit_exceeded:
        report = pipeline_process._format_limit_violation_report(limit_violations)
        if report:
            print(report, file=sys.stderr)
    run_overrides = dict(plan["run_overrides"])
    if parent_task_id:
        run_overrides["run.clearml.parent_task_id"] = parent_task_id
    data_overrides = plan["data_overrides"]
    downstream_data_overrides = plan["downstream_data_overrides"]
    eval_overrides = plan["eval_overrides"]
    queues = plan["queues"]
    steps = plan["steps"]

    step_task_ids: dict[str, str] = {}
    executed_jobs = 0

    if not plan["plan_only"] and not limit_exceeded:
        pipeline_queue = pipeline_process._select_queue(queues, "pipeline")
        queue_candidates = [
            pipeline_queue,
            pipeline_process._select_queue(queues, "preprocess"),
            pipeline_process._select_queue(queues, "train_model"),
            pipeline_process._select_queue(queues, "train_ensemble"),
            pipeline_process._normalize_str(queues.get("train_model_heavy")),
            pipeline_process._select_queue(queues, "leaderboard"),
            pipeline_process._select_queue(queues, "infer"),
        ]
        queue_name = next((value for value in queue_candidates if value), None)
        if not queue_name:
            model_variant_queues = queues.get("model_variants") or {}
            for value in model_variant_queues.values():
                value = pipeline_process._normalize_str(value)
                if value:
                    queue_name = value
                    break

        pipeline_name = pipeline_process._normalize_str(
            pipeline_process._cfg_value(cfg, "run.clearml.task_name")
        ) or "pipeline"
        if controller is None:
            pipeline_template_id = resolve_template_task_id(cfg, "pipeline")
            pipeline_project = pipeline_process._resolve_step_project_name(
                cfg, process_name="pipeline", train_project_per_preprocess=True
            )
            controller = create_pipeline_controller_from_template(
                cfg,
                base_task_id=pipeline_template_id,
                name=pipeline_name,
                project=pipeline_project,
                default_queue=pipeline_queue,
            )
        applied_steps_limit = apply_pipeline_parallelism(
            controller, max_concurrent_steps=parallelism["max_concurrent_steps"]
        )
        if not applied_steps_limit:
            pipeline_process._apply_parallelism_dependencies(
                plan,
                max_concurrent_steps=parallelism["max_concurrent_steps"],
                max_concurrent_train=0,
            )
        pipeline_process._apply_parallelism_dependencies(
            plan,
            max_concurrent_steps=0,
            max_concurrent_train=parallelism["max_concurrent_train"],
        )
        controller_overrides = pipeline_process._hydra_task_overrides()
        if controller_overrides:
            pipeline_process._ensure_override(controller_overrides, "task", "pipeline")
            pipeline_process._ensure_override(controller_overrides, "run.grid_run_id", grid_run_id)
            pipeline_process._ensure_override(
                controller_overrides, "run.output_dir", pipeline_process._cfg_value(cfg, "run.output_dir")
            )
            pipeline_process._ensure_override(controller_overrides, "run.clearml.enabled", True)
            pipeline_process._ensure_override(
                controller_overrides,
                "run.clearml.execution",
                controller_execution or pipeline_process._cfg_value(cfg, "run.clearml.execution"),
            )
            pipeline_process._ensure_override(controller_overrides, "pipeline.run_preprocess", plan.get("run_preprocess"))
            pipeline_process._ensure_override(controller_overrides, "pipeline.run_train", plan.get("run_train"))
            pipeline_process._ensure_override(
                controller_overrides, "pipeline.run_leaderboard", plan.get("run_leaderboard")
            )
            pipeline_process._ensure_override(controller_overrides, "pipeline.run_infer", plan.get("run_infer"))
            pipeline_process._ensure_override(
                controller_overrides,
                "pipeline.grid.preprocess_variants",
                plan.get("preprocess_variants"),
            )
            pipeline_process._ensure_override(
                controller_overrides,
                "pipeline.grid.model_variants",
                plan.get("model_variants"),
            )
            pipeline_process._ensure_override(controller_overrides, "data.dataset_path", pipeline_process._cfg_value(cfg, "data.dataset_path"))
            pipeline_process._ensure_override(controller_overrides, "data.target_column", pipeline_process._cfg_value(cfg, "data.target_column"))
            pipeline_process._ensure_override(controller_overrides, "data.raw_dataset_id", pipeline_process._cfg_value(cfg, "data.raw_dataset_id"))
            pipeline_process._ensure_override(controller_overrides, "run.usecase_id", pipeline_process._cfg_value(cfg, "run.usecase_id"))
        else:
            controller_overrides_map = pipeline_process._merge_overrides(
                pipeline_process._collect_run_overrides(cfg, grid_run_id, child_execution=None),
                pipeline_process._collect_data_overrides(cfg),
                pipeline_process._collect_eval_overrides(cfg),
                {
                    "task": "pipeline",
                    "run.output_dir": pipeline_process._cfg_value(cfg, "run.output_dir"),
                    "pipeline.run_preprocess": plan.get("run_preprocess"),
                    "pipeline.run_train": plan.get("run_train"),
                    "pipeline.run_leaderboard": plan.get("run_leaderboard"),
                    "pipeline.run_infer": plan.get("run_infer"),
                    "pipeline.grid.preprocess_variants": plan.get("preprocess_variants"),
                    "pipeline.grid.model_variants": plan.get("model_variants"),
                },
            )
            controller_overrides = pipeline_process._overrides_to_args(controller_overrides_map)
        if controller_overrides:
            apply_clearml_task_overrides(controller, controller_overrides)
        pipeline_require_clearml_agent(queue_name)

        template_task_ids = _resolve_template_task_ids(cfg, plan)

        def _base_task_kwargs(task_name: str) -> dict[str, Any]:
            task_id = template_task_ids.get(task_name)
            if not task_id:
                raise ValueError(f"template task_id is missing for process={task_name}.")
            return {"base_task_id": task_id}

        if plan["run_preprocess"]:
            for step in steps["preprocess"]:
                overrides = pipeline_process._merge_overrides(run_overrides, downstream_data_overrides, step["overrides"])
                _add_pipeline_step(
                    controller,
                    name=step["step_name"],
                    parents=step["parents"],
                    parameter_override={f"Args/{k}": v for k, v in pipeline_process._overrides_to_params(overrides).items()},
                    clone_base_task=True,
                    cache_executed_step=False,
                    execution_queue=step["queue"],
                    **_base_task_kwargs(step["task_name"]),
                )

        if plan["run_train"]:
            if not steps["train"]:
                raise ValueError("preprocess outputs are required before train.")
            for step in steps["train"]:
                overrides = pipeline_process._merge_overrides(
                    run_overrides,
                    downstream_data_overrides,
                    eval_overrides,
                    step["overrides"],
                )
                _add_pipeline_step(
                    controller,
                    name=step["step_name"],
                    parents=step["parents"],
                    parameter_override={f"Args/{k}": v for k, v in pipeline_process._overrides_to_params(overrides).items()},
                    clone_base_task=True,
                    cache_executed_step=False,
                    execution_queue=step["queue"],
                    **_base_task_kwargs(step["task_name"]),
                )

        if plan.get("run_ensemble"):
            if not steps.get("ensemble"):
                raise ValueError("train outputs are required before ensemble.")
            for step in steps["ensemble"]:
                overrides = pipeline_process._merge_overrides(
                    run_overrides,
                    eval_overrides,
                    step["overrides"],
                )
                _add_pipeline_step(
                    controller,
                    name=step["step_name"],
                    parents=step["parents"],
                    parameter_override={f"Args/{k}": v for k, v in pipeline_process._overrides_to_params(overrides).items()},
                    clone_base_task=True,
                    cache_executed_step=False,
                    execution_queue=step["queue"],
                    **_base_task_kwargs(step["task_name"]),
                )

        if plan["run_leaderboard"]:
            if not steps["train"]:
                raise ValueError("train outputs are required before leaderboard.")
            step = steps["leaderboard"]
            if step is None:
                raise ValueError("leaderboard step is missing.")
            train_task_refs = [
                pipeline_step_task_id_ref(train_step["step_name"]) for train_step in steps["train"]
            ]
            if plan.get("run_ensemble"):
                train_task_refs.extend(
                    pipeline_step_task_id_ref(ensemble_step["step_name"])
                    for ensemble_step in steps["ensemble"]
                )
            overrides = pipeline_process._merge_overrides(
                run_overrides,
                eval_overrides,
                step["overrides"],
                {"leaderboard.train_task_ids": train_task_refs},
            )
            _add_pipeline_step(
                controller,
                name=step["step_name"],
                parents=step["parents"],
                parameter_override={f"Args/{k}": v for k, v in pipeline_process._overrides_to_params(overrides).items()},
                clone_base_task=True,
                cache_executed_step=False,
                execution_queue=step["queue"],
                **_base_task_kwargs(step["task_name"]),
            )

        if plan["run_infer"]:
            step = steps["infer"]
            if step is None:
                raise ValueError("infer step is missing.")
            infer_cfg = getattr(cfg, "infer", None)
            overrides = pipeline_process._merge_overrides(run_overrides, step["overrides"])
            infer_model_id = pipeline_process._normalize_str(getattr(infer_cfg, "model_id", None))
            infer_train_task_id = pipeline_process._normalize_str(getattr(infer_cfg, "train_task_id", None))
            if infer_train_task_id:
                overrides["infer.train_task_id"] = infer_train_task_id
            elif infer_model_id:
                overrides["infer.model_id"] = infer_model_id
            else:
                raise ValueError("infer requires model_id or train_task_id for remote execution.")
            _add_pipeline_step(
                controller,
                name=step["step_name"],
                parents=step["parents"],
                parameter_override={f"Args/{k}": v for k, v in pipeline_process._overrides_to_params(overrides).items()},
                clone_base_task=True,
                cache_executed_step=False,
                execution_queue=step["queue"],
                **_base_task_kwargs(step["task_name"]),
            )

        if run_controller_locally:
            starter = getattr(controller, "start_locally", None)
            if not callable(starter):
                raise AttributeError("Pipeline controller does not support start_locally.")
            starter(run_pipeline_steps_locally=False)
        else:
            starter = getattr(controller, "start", None)
            if not callable(starter):
                raise AttributeError("Pipeline controller does not support start.")
            if queue_name:
                starter(queue=queue_name)
            else:
                starter()
        step_task_ids = _collect_step_task_ids(controller)
        executed_jobs = len(steps["train"])

    dataset_register_ref = None
    preprocess_refs: list[dict[str, Any]] = []
    train_refs: list[dict[str, Any]] = []
    ensemble_refs: list[dict[str, Any]] = []
    leaderboard_ref = None
    infer_ref = None
    if not plan["plan_only"]:
        for step in steps["preprocess"]:
            preprocess_refs.append(
                pipeline_process._build_ref(
                    run_dir=step["run_dir"],
                    task_id=step_task_ids.get(step["step_name"]),
                    preprocess_variant=step.get("preprocess_variant"),
                )
            )

        for step in steps["train"]:
            train_refs.append(
                pipeline_process._build_ref(
                    run_dir=step["run_dir"],
                    task_id=step_task_ids.get(step["step_name"]),
                    preprocess_variant=step.get("preprocess_variant"),
                    model_variant=step.get("model_variant"),
                    hpo_run_id=step.get("hpo_run_id"),
                    hpo_params=step.get("hpo_params"),
                )
            )

        for step in steps.get("ensemble") or []:
            ensemble_refs.append(
                pipeline_process._build_ref(
                    run_dir=step["run_dir"],
                    task_id=step_task_ids.get(step["step_name"]),
                    preprocess_variant=step.get("preprocess_variant"),
                )
            )

        if steps["leaderboard"] is not None:
            leaderboard_step = steps["leaderboard"]
            leaderboard_ref = pipeline_process._build_ref(
                run_dir=leaderboard_step["run_dir"],
                task_id=step_task_ids.get(leaderboard_step["step_name"]),
            )

        if steps["infer"] is not None:
            infer_step = steps["infer"]
            infer_ref = pipeline_process._build_ref(
                run_dir=infer_step["run_dir"],
                task_id=step_task_ids.get(infer_step["step_name"]),
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
            "fail_policy": pipeline_process._resolve_fail_policy(cfg),
        },
    }
    return pipeline_run
