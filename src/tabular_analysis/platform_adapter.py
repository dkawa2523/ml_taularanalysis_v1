"""ml-platform との接続面（Adapter）。

この Solution Repo は dkawa2523/ml_platform_v1（P201〜P204 反映済み）を前提とします。

ただし、platform 側の実装詳細（モジュールパスや関数名）は将来変わり得るため、
Solution 側は **この adapter を唯一の依存点**にしておくことで影響範囲を最小化します。

Codex タスクでは、まずこの adapter を platform 実装に合わせて完成させ、
以降の各プロセス（dataset_register/preprocess/train/...）は adapter だけを呼ぶようにします。

期待する platform 能力（P201〜P204 相当）:
- ClearML Task 初期化（project/name/tags/properties の統一）
- config_resolved.yaml の保存
- out.json / manifest.json の生成（hashes: config_hash/split_hash/recipe_hash など）
- （できれば）contract lint / doctor
"""

from __future__ import annotations

from collections.abc import Iterable as IterableABC, Sequence as SequenceABC
from datetime import datetime, timezone
import json
from dataclasses import dataclass
import os
import sys
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse, urlunparse
from typing import Any, Iterable, Mapping, Optional


@dataclass
class TaskContext:
    """実行コンテキスト（ClearML Task など）。

    clearml が無効（local 実行）の場合は task=None になります。
    """

    task: Any | None
    project_name: str
    task_name: str
    output_dir: Path


@dataclass(frozen=True)
class ClearMLScriptSpec:
    repository: str | None
    branch: str | None
    entry_point: str | None
    working_dir: str | None
    version_policy: str
    version_num: str | None


class PlatformAdapterError(RuntimeError):
    pass


_CLEARML_TASK_CACHE: dict[str, Any] = {}


def _cfg_value(cfg: Any, dotted_path: str, default: Any | None = None) -> Any:
    if cfg is None:
        return default
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None:
        try:
            value = OmegaConf.select(cfg, dotted_path)
        except Exception:
            value = None
        if value is not None:
            return value
    current = cfg
    for key in dotted_path.split("."):
        if isinstance(current, Mapping):
            if key not in current:
                return default
            current = current[key]
            continue
        if not hasattr(current, key):
            return default
        current = getattr(current, key)
    return current


def _in_docker() -> bool:
    return Path("/.dockerenv").exists()


def _normalize_files_host(url: str, *, port_override: int | None = None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = parsed.hostname
    if not host:
        return None
    scheme = parsed.scheme or "http"
    port = parsed.port
    if port_override is not None:
        port = port_override
    if port is None:
        port = 8081
    return f"{scheme}://{host}:{port}"


def _read_clearml_config_api_section() -> dict[str, str]:
    cfg_path = os.getenv("CLEARML_CONFIG_FILE")
    candidates = []
    if cfg_path:
        candidates.append(Path(cfg_path).expanduser())
    candidates.extend(
        [
            Path.cwd() / "clearml.conf",
            Path.home() / "clearml.conf",
            Path.home() / ".clearml.conf",
            Path.home() / ".config" / "clearml.conf",
        ]
    )
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            import configparser

            parser = configparser.ConfigParser()
            parser.read(candidate)
            if "api" in parser:
                return dict(parser["api"])
        except Exception:
            continue
    return {}


def _resolve_clearml_files_host_fallback() -> str | None:
    api_section = _read_clearml_config_api_section()
    files_host = os.getenv("CLEARML_FILES_HOST") or api_section.get("files_server") or api_section.get("files")
    if files_host:
        normalized = _normalize_files_host(files_host)
        if normalized and urlparse(normalized).hostname not in {"localhost", "127.0.0.1"}:
            return normalized

    api_host = os.getenv("CLEARML_API_HOST") or os.getenv("CLEARML_WEB_HOST")
    if not api_host:
        api_host = api_section.get("host") or api_section.get("api_server") or api_section.get("web_server")
    if api_host:
        parsed = urlparse(api_host if "://" in api_host else f"http://{api_host}")
        host = parsed.hostname
        if host and host not in {"localhost", "127.0.0.1"}:
            port = parsed.port
            if port is None or port in {8008, 8080}:
                port = 8081
            return _normalize_files_host(api_host, port_override=port)

    return None


def _apply_clearml_files_host_substitution() -> None:
    in_docker = _in_docker()
    try:
        from clearml.backend_api.session import Session  # type: ignore
        from clearml.storage.helper import StorageHelper  # type: ignore
    except Exception:
        return

    try:
        files_host = Session.get_files_server_host()
    except Exception:
        files_host = None

    normalized = _normalize_files_host(files_host or "")
    if normalized:
        host = urlparse(normalized).hostname
        if host in {"localhost", "127.0.0.1"}:
            normalized = None

    if not normalized:
        normalized = _resolve_clearml_files_host_fallback()
    if not normalized:
        if in_docker:
            return
        normalized = _normalize_files_host(
            os.getenv("CLEARML_FILES_HOST") or _read_clearml_config_api_section().get("files_server") or ""
        )
        if not normalized:
            return

    os.environ.setdefault("CLEARML_FILES_HOST", normalized)
    try:
        existing = {rule.registered_prefix: rule.local_prefix for rule in StorageHelper._path_substitutions}
    except Exception:
        existing = {}
    extra_prefixes: tuple[str, ...] = ()
    if not in_docker and urlparse(normalized).hostname in {"localhost", "127.0.0.1"}:
        extra_prefixes = (
            "http://host.docker.internal:8081",
            "https://host.docker.internal:8081",
        )
    for prefix in (
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "https://localhost:8081",
        "https://127.0.0.1:8081",
        *extra_prefixes,
    ):
        if existing.get(prefix) == normalized:
            continue
        try:
            StorageHelper.add_path_substitution(prefix, normalized)
        except Exception:
            continue


def _set_cfg_value(cfg: Any, dotted_path: str, value: Any) -> bool:
    if cfg is None:
        return False
    try:
        from omegaconf import OmegaConf  # type: ignore
    except Exception:
        OmegaConf = None
    if OmegaConf is not None and OmegaConf.is_config(cfg):
        try:
            was_struct = OmegaConf.is_struct(cfg)
        except Exception:
            was_struct = False
        if was_struct:
            try:
                OmegaConf.set_struct(cfg, False)
            except Exception:
                pass
        try:
            OmegaConf.update(cfg, dotted_path, value, merge=False)
            return True
        except Exception:
            return False
        finally:
            if was_struct:
                try:
                    OmegaConf.set_struct(cfg, True)
                except Exception:
                    pass
    current = cfg
    keys = dotted_path.split(".")
    for key in keys[:-1]:
        if isinstance(current, Mapping):
            if key not in current or not isinstance(current[key], Mapping):
                current[key] = {}
            current = current[key]
            continue
        if not hasattr(current, key) or getattr(current, key) is None:
            setattr(current, key, type("CfgNode", (), {})())
        current = getattr(current, key)
    last = keys[-1]
    if isinstance(current, Mapping):
        current[last] = value
        return True
    try:
        setattr(current, last, value)
        return True
    except Exception:
        return False


def _dedupe_tags(tags: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        if tag is None:
            continue
        tag_str = str(tag).strip()
        if not tag_str or tag_str in seen:
            continue
        seen.add(tag_str)
        result.append(tag_str)
    return result


def _normalize_requirement_lines(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        items: Iterable[Any] = values.splitlines()
    elif isinstance(values, Iterable) and not isinstance(values, Mapping):
        items = values
    else:
        items = [values]
    normalized: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if text.lstrip().startswith("#"):
            continue
        normalized.append(text)
    return normalized


def _resolve_repo_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    for base in candidates:
        for parent in [base, *base.parents]:
            if (parent / "conf").exists():
                return parent
    return Path.cwd()


def _run_git_command(cmd: Iterable[str]) -> str | None:
    try:
        proc = subprocess.run(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def _normalize_git_remote_url(value: str) -> str:
    text = value.strip()
    if text.startswith("git@") and ":" in text:
        host_part, path = text.split(":", 1)
        host = host_part.split("@", 1)[-1]
        text = f"https://{host}/{path}"
    elif text.startswith("ssh://") and "@" in text:
        rest = text[len("ssh://") :]
        host_part, _, path = rest.partition("/")
        host = host_part.split("@", 1)[-1]
        text = f"https://{host}/{path}"
    if text.endswith(".git"):
        text = text[:-4]
    return text


def detect_git_repository_url(repo_root: Path) -> str | None:
    value = _run_git_command(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
    if not value:
        return None
    return _normalize_git_remote_url(value)


def detect_git_branch(repo_root: Path) -> str | None:
    value = _run_git_command(["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"])
    if not value or value == "HEAD":
        return None
    return value


def _normalize_code_ref(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_clearml_repository(value: Any) -> str | None:
    text = _normalize_code_ref(value)
    if not text:
        return None
    return _normalize_git_remote_url(text).rstrip("/")


def normalize_clearml_branch(value: Any) -> str | None:
    return _normalize_code_ref(value)


def normalize_clearml_entry_point(value: Any) -> str | None:
    text = _normalize_code_ref(value)
    if not text:
        return None
    parts = text.split()
    if parts and parts[0] in {"python", "python3"}:
        parts = parts[1:]
    normalized = " ".join(parts).strip()
    if not normalized:
        return None
    command, _ = _split_entry_point_command(normalized)
    return command or None


def normalize_clearml_version_num(value: Any) -> str | None:
    return _normalize_code_ref(value)


def hydra_list(values: list[str]) -> str:
    return "[" + ",".join(values) + "]"


def _parse_json_list(text: str) -> list[Any] | None:
    if not (text.startswith("[") and text.endswith("]")):
        return None
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    if isinstance(parsed, list):
        return parsed
    return None


def _split_bracket_list(text: str) -> list[str] | None:
    if not (text.startswith("[") and text.endswith("]")):
        return None
    inner = text[1:-1].strip()
    if not inner:
        return []
    items: list[str] = []
    for item in inner.split(","):
        cleaned = item.strip().strip("'\"").strip()
        if cleaned:
            items.append(cleaned)
    return items


def _coerce_hydra_list_value(value: Any) -> list[str]:
    if value is None:
        return []
    items: list[Any]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parsed = _parse_json_list(text)
        if parsed is None:
            parsed = _split_bracket_list(text)
        items = parsed if parsed is not None else [text]
    elif isinstance(value, Mapping):
        return []
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    elif isinstance(value, IterableABC):
        items = list(value)
    else:
        items = [value]
    normalized: list[str] = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        normalized.append(text)
    return normalized


_ENTRYPOINT_OVERRIDE_RE = re.compile(r"\s[+~]?[^\s=]+=")


def _split_entry_point_command(entry_point: str) -> tuple[str, str]:
    text = str(entry_point).strip()
    if not text:
        return ("", "")
    match = _ENTRYPOINT_OVERRIDE_RE.search(text)
    if not match:
        return (text, "")
    idx = match.start()
    return (text[:idx].strip(), text[idx:].strip())


def _swap_entry_point_command(entry_point: str, new_command: str) -> str:
    _, args = _split_entry_point_command(entry_point)
    if not new_command:
        return entry_point
    if args:
        return f"{new_command.strip()} {args}"
    return new_command.strip()


def _replace_or_append_override(entry_point: str, key: str, value: str) -> str:
    if not entry_point:
        return f"{key}={value}"
    list_pattern = re.compile(
        rf"(?<!\S)({re.escape(key)}=)(['\"]?\[[^\]]*\]['\"]?)"
    )
    if list_pattern.search(entry_point):
        return list_pattern.sub(rf"\1{value}", entry_point)
    scalar_pattern = re.compile(rf"(?<!\S)({re.escape(key)}=)([^\s]+)")
    if scalar_pattern.search(entry_point):
        return scalar_pattern.sub(rf"\1{value}", entry_point)
    return f"{entry_point} {key}={value}"


def _canonicalize_pipeline_entrypoint(
    cfg: Any,
    entry_point: str | None,
    fallback: str | None,
    task_name_override: str | None = None,
    canonicalize_pipeline: bool = True,
) -> str | None:
    if not canonicalize_pipeline:
        return entry_point
    task_name = _normalize_code_ref(task_name_override) or _normalize_code_ref(
        _cfg_value(cfg, "task.name")
    )
    if task_name != "pipeline":
        return entry_point
    return entry_point or fallback or "tools/clearml_entrypoint.py"


def _resolve_clearml_entrypoint(
    cfg: Any,
    current_entry_point: Any,
    entry_point_override: str | None,
    task_name_override: str | None = None,
    canonicalize_pipeline: bool = True,
) -> str | None:
    current_text = _normalize_code_ref(current_entry_point)
    base = current_text
    if entry_point_override is not None:
        override_text = str(entry_point_override).strip()
        base = override_text or current_text
    return _canonicalize_pipeline_entrypoint(
        cfg,
        base,
        entry_point_override or current_text,
        task_name_override=task_name_override,
        canonicalize_pipeline=canonicalize_pipeline,
    )


def resolve_clearml_code_reference(cfg: Any) -> tuple[str | None, str | None]:
    repo_value = _normalize_code_ref(_cfg_value(cfg, "run.clearml.code_ref.repository"))
    branch_value = _normalize_code_ref(_cfg_value(cfg, "run.clearml.code_ref.branch"))
    if repo_value is None:
        repo_value = _normalize_code_ref(_cfg_value(cfg, "run.clearml.code_repository"))
    if branch_value is None:
        branch_value = _normalize_code_ref(_cfg_value(cfg, "run.clearml.code_branch"))
    repo_root = _resolve_repo_root()
    if repo_value and repo_value.lower() == "auto":
        repo_value = detect_git_repository_url(repo_root)
    if branch_value and branch_value.lower() == "auto":
        branch_value = detect_git_branch(repo_root)
    return repo_value, branch_value


def _resolve_clearml_entrypoint_override(cfg: Any) -> str | None:
    execution_value = _normalize_code_ref(_cfg_value(cfg, "run.clearml.execution"))
    if execution_value is None:
        return None
    execution = execution_value.lower()
    if execution in {"agent", "clone", "pipeline_controller", "pipeline_controller_local"}:
        return "tools/clearml_entrypoint.py"
    return None


def _resolve_clearml_code_version_mode(cfg: Any, *, override: str | None = None) -> str:
    text = _normalize_code_ref(override) or _normalize_code_ref(
        _cfg_value(cfg, "run.clearml.code_ref.mode")
    )
    if text is None:
        text = _normalize_code_ref(_cfg_value(cfg, "run.clearml.code_version_mode"))
    if not text:
        return "branch_head"
    lowered = text.lower()
    if lowered in {"branch_head", "branch", "head"}:
        return "branch_head"
    if lowered in {"pin_commit", "commit", "pinned"}:
        return "pin_commit"
    if lowered in {"none", "off", "disabled"}:
        return "none"
    return "branch_head"


def _resolve_clearml_version_num(
    cfg: Any,
    *,
    version_mode_override: str | None = None,
) -> tuple[str, str | None]:
    mode = _resolve_clearml_code_version_mode(cfg, override=version_mode_override)
    if mode == "pin_commit":
        commit_override = _normalize_code_ref(_cfg_value(cfg, "run.clearml.code_ref.commit"))
        if commit_override and commit_override.lower() != "auto":
            return mode, commit_override
        repo_root = _resolve_repo_root()
        commit = _run_git_command(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        if not commit:
            raise PlatformAdapterError("Failed to resolve git commit for pin_commit.")
        return mode, commit
    if mode == "none":
        return mode, None
    return mode, ""


def resolve_clearml_script_spec(
    cfg: Any,
    *,
    current_entry_point: Any | None = None,
    repo_override: str | None = None,
    branch_override: str | None = None,
    entry_point_override: str | None = None,
    working_dir_override: str | None = None,
    version_mode_override: str | None = None,
    task_name_override: str | None = None,
    canonicalize_pipeline: bool = True,
) -> ClearMLScriptSpec:
    repo_value, branch_value = resolve_clearml_code_reference(cfg)
    if repo_override is not None:
        repo_value = repo_override
    if branch_override is not None:
        branch_value = branch_override
    entry_override = (
        entry_point_override
        if entry_point_override is not None
        else _resolve_clearml_entrypoint_override(cfg)
    )
    entry_point = _resolve_clearml_entrypoint(
        cfg,
        current_entry_point,
        entry_override,
        task_name_override=task_name_override,
        canonicalize_pipeline=canonicalize_pipeline,
    )
    working_dir = _normalize_code_ref(working_dir_override) or _normalize_code_ref(
        _cfg_value(cfg, "run.clearml.working_dir")
    )
    version_policy, version_num = _resolve_clearml_version_num(
        cfg, version_mode_override=version_mode_override
    )
    return ClearMLScriptSpec(
        repository=repo_value,
        branch=branch_value,
        entry_point=entry_point,
        working_dir=working_dir,
        version_policy=version_policy,
        version_num=version_num,
    )


def _commit_matches(expected: str | None, actual: str | None) -> bool:
    if not expected:
        return not actual
    if not actual:
        return False
    expected_norm = expected.lower()
    actual_norm = actual.lower()
    if expected_norm == actual_norm:
        return True
    if expected_norm.startswith(actual_norm) or actual_norm.startswith(expected_norm):
        return min(len(expected_norm), len(actual_norm)) >= 7
    return False


def clearml_script_mismatches(spec: ClearMLScriptSpec, script: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_repo = normalize_clearml_repository(spec.repository)
    if expected_repo:
        actual_repo = normalize_clearml_repository(script.get("repository"))
        if actual_repo != expected_repo:
            errors.append(f"repository mismatch: {actual_repo or 'none'}")
    expected_branch = normalize_clearml_branch(spec.branch)
    if expected_branch:
        actual_branch = normalize_clearml_branch(script.get("branch"))
        if actual_branch != expected_branch:
            errors.append(f"branch mismatch: {actual_branch or 'none'}")
    expected_entry = normalize_clearml_entry_point(spec.entry_point)
    if expected_entry:
        actual_entry = normalize_clearml_entry_point(script.get("entry_point"))
        if actual_entry != expected_entry:
            errors.append(f"entry_point mismatch: {actual_entry or 'none'}")
    expected_working = _normalize_code_ref(spec.working_dir)
    if expected_working:
        actual_working = _normalize_code_ref(script.get("working_dir"))
        if actual_working != expected_working:
            errors.append(f"working_dir mismatch: {actual_working or 'none'}")
    actual_version = normalize_clearml_version_num(script.get("version_num"))
    if spec.version_policy == "branch_head":
        if actual_version:
            errors.append(f"version_num mismatch: {actual_version}")
    elif spec.version_policy == "none":
        return errors
    elif spec.version_policy == "pin_commit":
        expected_version = normalize_clearml_version_num(spec.version_num)
        if not _commit_matches(expected_version, actual_version):
            errors.append(f"version_num mismatch: {actual_version or 'none'}")
    return errors


def _resolve_clearml_task(target: Any) -> Any:
    for name in ("task", "_task", "pipeline_task"):
        if hasattr(target, name):
            value = getattr(target, name)
            if value is not None:
                return value
    return target


def _set_clearml_task_script(task: Any, payload: Mapping[str, Any]) -> None:
    setter = getattr(task, "set_script", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_script is not available.")
    try:
        setter(**payload)
        return
    except TypeError:
        pass
    if "version_num" in payload:
        commit_payload = dict(payload)
        commit_payload["commit"] = commit_payload.pop("version_num")
        try:
            setter(**commit_payload)
            return
        except TypeError:
            pass
    try:
        setter(script=dict(payload))
        return
    except TypeError:
        if "version_num" not in payload:
            raise
        trimmed = dict(payload)
        trimmed.pop("version_num", None)
        setter(**trimmed)


def _apply_clearml_task_script_override(target: Any, cfg: Any) -> bool:
    task = _resolve_clearml_task(target)
    current = _task_script(task)
    current_repo = current.get("repository")
    current_branch = current.get("branch")
    current_entry_point = current.get("entry_point")
    current_version = current.get("version_num")
    spec = resolve_clearml_script_spec(cfg, current_entry_point=current_entry_point)
    changed = False
    if spec.repository is not None and str(current_repo or "") != str(spec.repository):
        changed = True
    if spec.branch is not None and str(current_branch or "") != str(spec.branch):
        changed = True
    if spec.entry_point is not None and str(current_entry_point or "") != str(spec.entry_point):
        changed = True
    if spec.version_num is not None:
        current_text = "" if current_version is None else str(current_version)
        if current_version is None or current_text != str(spec.version_num):
            changed = True
    if not changed:
        return False
    setter = getattr(task, "set_script", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_script is not available.")
    payload: dict[str, Any] = {}
    repo_to_set = spec.repository if spec.repository is not None else current_repo
    branch_to_set = spec.branch if spec.branch is not None else current_branch
    if repo_to_set is not None:
        payload["repository"] = str(repo_to_set)
    if branch_to_set is not None:
        payload["branch"] = str(branch_to_set)
    entry_point = spec.entry_point if spec.entry_point is not None else current_entry_point
    if entry_point is not None:
        payload["entry_point"] = str(entry_point)
    working_dir = spec.working_dir if spec.working_dir is not None else current.get("working_dir")
    if working_dir is not None:
        payload["working_dir"] = working_dir
    if spec.version_num is not None:
        payload["version_num"] = spec.version_num
    if not payload:
        return False
    _set_clearml_task_script(task, payload)
    return True


def _apply_clearml_task_args(task: Any, args: Mapping[str, Any]) -> bool:
    if not args:
        return False
    params = _task_parameters(task)
    existing_args: dict[str, str] = {}
    for key, value in params.items():
        if isinstance(key, str) and key.startswith("Args/"):
            existing_args[key[5:]] = "" if value is None else str(value)
    updates: dict[str, str] = {}
    for key, value in args.items():
        expected = "" if value is None else str(value)
        if existing_args.get(str(key)) != expected:
            updates[str(key)] = expected
    if not updates:
        return False
    updated_params = dict(params)
    for key, value in updates.items():
        updated_params[f"Args/{key}"] = value
    setter = getattr(task, "set_parameters", None)
    if callable(setter):
        setter(updated_params)
        return True
    setter = getattr(task, "set_parameters_as_dict", None)
    if callable(setter):
        merged = {**existing_args, **updates}
        setter({"Args": merged})
        return True
    raise PlatformAdapterError("ClearML Task.set_parameters is not available.")


def _apply_clearml_pipeline_args(target: Any, cfg: Any) -> bool:
    task = _resolve_clearml_task(target)
    preprocess_variants = _coerce_hydra_list_value(
        _cfg_value(cfg, "pipeline.grid.preprocess_variants")
    )
    model_variants = _coerce_hydra_list_value(
        _cfg_value(cfg, "pipeline.grid.model_variants")
    )
    if not preprocess_variants and not model_variants:
        return False
    args: dict[str, Any] = {}
    if preprocess_variants:
        args["pipeline.grid.preprocess_variants"] = hydra_list(preprocess_variants)
    if model_variants:
        args["pipeline.grid.model_variants"] = hydra_list(model_variants)
    return _apply_clearml_task_args(task, args)


def _apply_clearml_task_requirements(task: Any, requirements: Iterable[str]) -> bool:
    normalized = _normalize_requirement_lines(requirements)
    if not normalized:
        return False
    setter = getattr(task, "set_packages", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_packages is not available.")
    try:
        setter(normalized)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to set task requirements via ClearML: {exc}") from exc
    return True


def _resolve_clearml_pipeline_requirements(cfg: Any) -> list[str]:
    repo_root = _resolve_repo_root()
    spec_path = repo_root / "conf" / "clearml" / "templates.yaml"
    try:
        from tabular_analysis.clearml import template_manager  # type: ignore

        ctx = template_manager.load_default_context(repo_root)
        specs = template_manager.load_template_specs(spec_path, ctx)
        for spec in specs:
            if spec.name == "pipeline":
                return list(spec.requirements or [])
    except Exception:
        pass
    return ["clearml>=1.15.0", "uv>=0.5.0"]


def _resolve_version_props(cfg: Any, *, clearml_enabled: bool) -> dict[str, str]:
    try:
        from ml_platform.versioning import (  # type: ignore
            get_code_version,
            get_platform_version,
            get_schema_version,
        )
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "ml_platform.versioning is required for ClearML runs. "
                "Install/update ml_platform."
            ) from exc
        return {"code_version": "unknown", "platform_version": "unknown", "schema_version": "unknown"}
    schema_version = _cfg_value(cfg, "run.schema_version") or get_schema_version(cfg, default="unknown")
    return {
        "code_version": get_code_version(repo_root=Path.cwd()),
        "platform_version": get_platform_version(),
        "schema_version": str(schema_version),
    }


def _build_properties(
    cfg: Any,
    *,
    stage: str,
    task_name: str,
    extra: Optional[Mapping[str, Any]],
    clearml_enabled: bool,
) -> dict[str, Any]:
    usecase_id = _cfg_value(cfg, "run.usecase_id") or _cfg_value(cfg, "usecase_id") or "unknown"
    process = _cfg_value(cfg, "task.name") or task_name or stage or "unknown"
    versions = _resolve_version_props(cfg, clearml_enabled=clearml_enabled)
    grid_run_id = _cfg_value(cfg, "run.grid_run_id")
    retrain_run_id = _cfg_value(cfg, "run.retrain_run_id")
    base: dict[str, Any] = {
        "usecase_id": usecase_id,
        "process": process,
        "schema_version": versions.get("schema_version", "unknown"),
        "code_version": versions.get("code_version", "unknown"),
        "platform_version": versions.get("platform_version", "unknown"),
        "grid_run_id": grid_run_id,
    }
    if retrain_run_id:
        base["retrain_run_id"] = retrain_run_id
    merged = dict(base)
    if extra:
        merged.update(dict(extra))
    for key, value in base.items():
        merged.setdefault(key, value)
    return merged


def _build_tags(
    cfg: Any,
    *,
    process: str,
    schema_version: str,
    grid_run_id: Any,
    retrain_run_id: Any,
    extra_tags: Optional[Iterable[str]],
    tags: Optional[Iterable[str]],
) -> list[str]:
    usecase_id = _cfg_value(cfg, "run.usecase_id") or _cfg_value(cfg, "usecase_id") or "unknown"
    base = [
        f"usecase:{usecase_id}",
        f"process:{process}",
        f"schema:{schema_version}",
    ]
    if grid_run_id:
        base.append(f"grid:{grid_run_id}")
    if retrain_run_id:
        base.append(f"retrain:{retrain_run_id}")
    return _dedupe_tags([*base, *(extra_tags or []), *(tags or [])])


def _ensure_clearml_names(cfg: Any, *, project_name: str, task_name: str, clearml_enabled: bool) -> None:
    if _cfg_value(cfg, "run.clearml.project_name") != project_name:
        _set_cfg_value(cfg, "run.clearml.project_name", project_name)
    if _cfg_value(cfg, "run.clearml.task_name") != task_name:
        _set_cfg_value(cfg, "run.clearml.task_name", task_name)
    if clearml_enabled:
        if _cfg_value(cfg, "run.clearml.project_name") != project_name:
            raise PlatformAdapterError("Failed to set run.clearml.project_name for ClearML init.")
        if _cfg_value(cfg, "run.clearml.task_name") != task_name:
            raise PlatformAdapterError("Failed to set run.clearml.task_name for ClearML init.")


def _load_clearml_module(clearml_enabled: bool):
    try:
        from ml_platform.integrations import clearml as platform_clearml  # type: ignore
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "ml_platform.integrations.clearml is required for ClearML runs. "
                "Install/update ml_platform."
            ) from exc
        return None
    _patch_platform_clearml(platform_clearml)
    return platform_clearml


def _normalize_clearml_user_properties(properties: Mapping[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in properties.items():
        if isinstance(value, Mapping) and "value" in value:
            value = value.get("value")
        normalized[str(key)] = "" if value is None else str(value)
    return normalized


def _patch_platform_clearml(platform_clearml: Any) -> None:
    if platform_clearml is None:
        return
    if getattr(platform_clearml, "_ta_user_properties_patch", False):
        return

    def _safe_set_user_properties(task: Any, properties: Mapping[str, Any] | None) -> None:
        if not properties:
            return
        setter = getattr(task, "set_user_properties", None)
        if not callable(setter):
            return
        normalized = _normalize_clearml_user_properties(dict(properties))
        try:
            setter(**normalized)
            return
        except TypeError:
            pass
        try:
            setter(*normalized.items())
            return
        except TypeError:
            setter(normalized)

    platform_clearml.set_user_properties = _safe_set_user_properties
    platform_clearml._ta_user_properties_patch = True


def _load_clearml_dataset(clearml_enabled: bool):
    try:
        from clearml import Dataset as ClearMLDataset  # type: ignore
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "clearml.Dataset is required for ClearML dataset registration. "
                "Install/update clearml."
            ) from exc
        return None
    return ClearMLDataset


def _existing_user_properties(task: Any) -> dict[str, Any]:
    getter = getattr(task, "get_user_properties", None)
    if callable(getter):
        try:
            existing = getter()
        except Exception:
            existing = None
        if isinstance(existing, Mapping):
            return dict(existing)
    return {}


def clearml_task_type_controller() -> str:
    return "controller"


def _apply_clearml_system_tags(task: Any, system_tags: Iterable[str] | None) -> None:
    if not system_tags:
        return
    getter = getattr(task, "get_system_tags", None)
    setter = getattr(task, "set_system_tags", None)
    if not callable(getter) or not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_system_tags is not available.")
    try:
        current = getter() or []
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to read ClearML system tags: {exc}") from exc
    merged = _dedupe_tags([*current, *system_tags])
    try:
        setter(merged)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to set ClearML system tags: {exc}") from exc


def _ensure_clearml_project_system_tags(
    project_name: str | None,
    add_tags: Iterable[str] | None = None,
    *,
    remove_tags: Iterable[str] | None = None,
) -> None:
    if not project_name:
        return
    add_list = _dedupe_tags(add_tags or [])
    remove_set = {tag for tag in _dedupe_tags(remove_tags or []) if tag}
    if not add_list and not remove_set:
        return
    try:
        from clearml.backend_api.session import Session  # type: ignore
    except Exception:
        return
    try:
        session = Session()
    except Exception as exc:
        print(f"[warn] ClearML Session init failed for project tags: {exc}", file=sys.stderr)
        return
    project: Mapping[str, Any] | None = None
    project_id: str | None = None
    looks_like_id = "/" not in project_name and len(project_name) in {24, 32}
    if looks_like_id:
        project_id = project_name
    if project_id is None:
        try:
            response = session.send_request(
                service="projects",
                action="get_all",
                json={"name": project_name, "search_hidden": True, "size": 10},
            )
        except Exception as exc:
            print(f"[warn] ClearML project lookup failed: {exc}", file=sys.stderr)
            return
        if not getattr(response, "ok", False):
            return
        try:
            payload = response.json() or {}
        except Exception:
            payload = {}
        projects: list[Mapping[str, Any]] = []
        if isinstance(payload, Mapping) and isinstance(payload.get("projects"), list):
            projects = [proj for proj in payload.get("projects", []) if isinstance(proj, Mapping)]
        elif isinstance(payload, Mapping) and isinstance(payload.get("data"), Mapping):
            candidates = payload.get("data", {}).get("projects")
            if isinstance(candidates, list):
                projects = [proj for proj in candidates if isinstance(proj, Mapping)]
        if projects:
            for candidate in projects:
                name = candidate.get("name") or candidate.get("full_name") or candidate.get("path")
                if name == project_name:
                    project = candidate
                    break
            if project is None:
                project = projects[0]
            project_id = project.get("id") or project.get("project") or project.get("project_id")
    if project_id and project is None:
        try:
            response = session.send_request(
                service="projects",
                action="get_by_id",
                json={"project": project_id},
            )
        except Exception as exc:
            print(f"[warn] ClearML project lookup by id failed: {exc}", file=sys.stderr)
            return
        if not getattr(response, "ok", False):
            return
        try:
            payload = response.json() or {}
        except Exception:
            payload = {}
        if isinstance(payload, Mapping) and isinstance(payload.get("project"), Mapping):
            project = payload.get("project")
        elif isinstance(payload, Mapping) and isinstance(payload.get("data"), Mapping):
            project = payload.get("data", {}).get("project")
    if not project_id:
        project_id = project.get("id") if project else None
    if not project_id:
        return
    system_tags = project.get("system_tags") or []
    if not isinstance(system_tags, list):
        try:
            system_tags = list(system_tags)
        except Exception:
            system_tags = []
    merged = _dedupe_tags([*system_tags, *add_list])
    if remove_set:
        merged = [tag for tag in merged if tag not in remove_set]
    if merged == system_tags:
        return
    try:
        update = session.send_request(
            service="projects",
            action="update",
            json={"project": project_id, "system_tags": merged},
        )
    except Exception as exc:
        print(f"[warn] ClearML project update failed: {exc}", file=sys.stderr)
        return
    if not getattr(update, "ok", False):
        print("[warn] ClearML project update returned non-ok response", file=sys.stderr)


def _apply_clearml_tags(task: Any, tags: Iterable[str] | None) -> None:
    tag_list = _dedupe_tags(tags or [])
    if not tag_list:
        return
    existing = _task_tags(task)
    merged = _dedupe_tags([*existing, *tag_list])
    setter = getattr(task, "set_tags", None)
    if callable(setter):
        try:
            setter(merged)
            return
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to set ClearML tags: {exc}") from exc
    adder = getattr(task, "add_tags", None)
    if not callable(adder):
        raise PlatformAdapterError("ClearML Task.add_tags is not available.")
    missing = [tag for tag in tag_list if tag not in existing]
    if not missing:
        return
    try:
        adder(missing)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to add ClearML tags: {exc}") from exc


def _apply_clearml_task_type(task: Any, task_type: str | None) -> None:
    if not task_type:
        return
    setter = getattr(task, "set_task_type", None)
    if not callable(setter):
        return
    try:
        from clearml import Task as ClearMLTask  # type: ignore

        normalized = task_type
        if isinstance(task_type, str) and task_type.lower() == "controller":
            normalized = ClearMLTask.TaskTypes.controller
        setter(normalized)
    except Exception:
        try:
            setter(task_type)
        except Exception:
            return


def hash_config(payload: Any) -> str:
    try:
        from ml_platform.artifacts import hash_config as platform_hash_config  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("ml_platform.artifacts.hash_config not available.") from exc
    return platform_hash_config(payload)


def hash_split(payload: Any) -> str:
    try:
        from ml_platform.artifacts import hash_split as platform_hash_split  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("ml_platform.artifacts.hash_split not available.") from exc
    return platform_hash_split(payload)


def hash_recipe(payload: Any) -> str:
    try:
        from ml_platform.artifacts import hash_recipe as platform_hash_recipe  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("ml_platform.artifacts.hash_recipe not available.") from exc
    return platform_hash_recipe(payload)


def is_clearml_enabled(cfg) -> bool:
    return bool(getattr(cfg.run.clearml, "enabled", False)) and str(
        getattr(cfg.run.clearml, "execution", "local")
    ) != "local"


def resolve_version_props(cfg: Any, *, clearml_enabled: Optional[bool] = None) -> dict[str, str]:
    if clearml_enabled is None:
        clearml_enabled = is_clearml_enabled(cfg)
    return _resolve_version_props(cfg, clearml_enabled=bool(clearml_enabled))


def resolve_output_dir(cfg, stage: str) -> Path:
    base = Path(getattr(cfg.run, "output_dir", "outputs"))
    return base / stage


def _capture_env_snapshot(ctx: TaskContext) -> None:
    try:
        from .ops.env_snapshot import capture_env_snapshot
    except Exception as exc:
        raise PlatformAdapterError("tabular_analysis.ops.env_snapshot is not available.") from exc
    try:
        env_path, freeze_path = capture_env_snapshot(ctx.output_dir)
        upload_artifact(ctx, env_path.name, env_path)
        upload_artifact(ctx, freeze_path.name, freeze_path)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to capture env snapshot: {exc}") from exc


def init_task_context(
    cfg,
    *,
    stage: str,
    task_name: str,
    tags: Optional[list[str]] = None,
    properties: Optional[dict] = None,
    task_type: str | None = None,
    system_tags: Optional[Iterable[str]] = None,
) -> TaskContext:
    """platform の task_factory を呼び出して Task を作る。

    - ClearML 無効の場合: task=None の TaskContext を返す
    - ClearML 有効の場合: platform の task_factory を呼び出す

    NOTE: platform 側 API パスが変わってもこの関数の中だけを直せばよい。
    """

    project_root = _cfg_value(cfg, "run.clearml.project_root") or "MFG"
    usecase_id = _cfg_value(cfg, "run.usecase_id") or "unknown"
    project_name = (
        _cfg_value(cfg, "run.clearml.project_name")
        or _cfg_value(cfg, "task.project_name")
        or f"{project_root}/TabularAnalysis/{usecase_id}/{stage}"
    )
    task_name_value = _cfg_value(cfg, "run.clearml.task_name") or task_name
    output_dir = resolve_output_dir(cfg, stage)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from .clearml.ui_logger import configure_reporting

        configure_reporting(cfg)
    except Exception:
        pass

    if not is_clearml_enabled(cfg):
        ctx = TaskContext(
            task=None,
            project_name=str(project_name),
            task_name=str(task_name_value),
            output_dir=output_dir,
        )
        _capture_env_snapshot(ctx)
        return ctx

    try:
        _ensure_clearml_names(
            cfg,
            project_name=str(project_name),
            task_name=str(task_name_value),
            clearml_enabled=True,
        )
        platform_clearml = _load_clearml_module(clearml_enabled=True)
        task_factory = getattr(platform_clearml, "task_factory", None)
        if task_factory is None:
            raise PlatformAdapterError("ml_platform.integrations.clearml.task_factory not found.")
        merged_props = _build_properties(
            cfg,
            stage=stage,
            task_name=str(task_name_value),
            extra=properties,
            clearml_enabled=True,
        )
        process = str(merged_props.get("process") or task_name_value or stage)
        merged_tags = _build_tags(
            cfg,
            process=process,
            schema_version=str(merged_props.get("schema_version") or "unknown"),
            grid_run_id=merged_props.get("grid_run_id"),
            retrain_run_id=merged_props.get("retrain_run_id"),
            extra_tags=_cfg_value(cfg, "run.clearml.extra_tags") or [],
            tags=tags,
        )
        reuse_last_task_id = None
        if not os.getenv("CLEARML_TASK_ID") and not os.getenv("TRAINS_TASK_ID"):
            reuse_last_task_id = False
        try:
            task = task_factory(
                cfg,
                tags=merged_tags,
                task_type=task_type,
                reuse_last_task_id=reuse_last_task_id,
            )
        except TypeError:
            task = task_factory(cfg, tags=merged_tags, reuse_last_task_id=reuse_last_task_id)
        _apply_clearml_task_type(task, task_type)
        _apply_clearml_task_script_override(task, cfg)
        _apply_clearml_system_tags(task, system_tags)
        setter = getattr(platform_clearml, "set_user_properties", None)
        if setter is None:
            raise PlatformAdapterError("ml_platform.integrations.clearml.set_user_properties not found.")
        existing = _existing_user_properties(task)
        merged_props = {**existing, **merged_props}
        setter(task, merged_props)
        ctx = TaskContext(
            task=task,
            project_name=str(project_name),
            task_name=str(task_name_value),
            output_dir=output_dir,
        )
    except Exception as e:
        raise PlatformAdapterError(f"Failed to init ClearML task via ml-platform: {e}") from e
    _capture_env_snapshot(ctx)
    return ctx


def save_config_resolved(ctx: TaskContext, cfg) -> Path:
    """Hydra の解決済み config を保存（platform に委譲できる場合は委譲）。"""
    if ctx.task is not None:
        try:
            from ml_platform.config import export_config_artifact  # type: ignore
        except Exception as exc:
            raise PlatformAdapterError(
                "ml_platform.config.export_config_artifact not available for ClearML runs."
            ) from exc
        try:
            return export_config_artifact(
                cfg,
                output_dir=ctx.output_dir,
                task=ctx.task,
                artifact_name="config_resolved.yaml",
            )
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to write config_resolved.yaml via ml_platform: {exc}") from exc
    path = ctx.output_dir / "config_resolved.yaml"
    try:
        from omegaconf import OmegaConf

        path.write_text(OmegaConf.to_yaml(cfg), encoding="utf-8")
    except Exception:
        path.write_text(str(cfg), encoding="utf-8")
    return path


def write_out_json(ctx: TaskContext, out: dict[str, Any]) -> Path:
    path = ctx.output_dir / "out.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if ctx.task is not None:
        platform_clearml = _load_clearml_module(clearml_enabled=True)
        uploader = getattr(platform_clearml, "upload_artifact", None)
        if uploader is None:
            raise PlatformAdapterError("ml_platform.integrations.clearml.upload_artifact not found.")
        try:
            uploader(ctx.task, "out.json", path)
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to upload out.json via ml_platform: {exc}") from exc
    return path


def upload_artifact(ctx: TaskContext, name: str, path: Path) -> None:
    """Upload an artifact to ClearML when enabled."""
    if ctx.task is None:
        return
    platform_clearml = _load_clearml_module(clearml_enabled=True)
    uploader = getattr(platform_clearml, "upload_artifact", None)
    if uploader is None:
        raise PlatformAdapterError("ml_platform.integrations.clearml.upload_artifact not found.")
    try:
        uploader(ctx.task, name, path)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to upload artifact {name} via ml_platform: {exc}") from exc


def update_task_properties(ctx: TaskContext, props: Mapping[str, Any]) -> None:
    """Merge and update task user properties (ClearML only)."""
    if ctx.task is None:
        return
    platform_clearml = _load_clearml_module(clearml_enabled=True)
    setter = getattr(platform_clearml, "set_user_properties", None)
    if setter is None:
        raise PlatformAdapterError("ml_platform.integrations.clearml.set_user_properties not found.")
    existing = _existing_user_properties(ctx.task)
    merged = {**existing, **dict(props)}
    try:
        setter(ctx.task, merged)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to update user properties via ml_platform: {exc}") from exc


def connect_hyperparameters(
    ctx: TaskContext,
    hparams: Mapping[str, Any],
    *,
    name: str | None = None,
) -> None:
    """Connect minimal HyperParameters to ClearML task."""
    if ctx.task is None:
        return
    connector = getattr(ctx.task, "connect", None)
    if not callable(connector):
        raise PlatformAdapterError("ClearML Task.connect is not available.")
    payload = dict(hparams)
    try:
        if name:
            connector(payload, name=name)
        else:
            connector(payload)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to connect HyperParameters via ClearML: {exc}") from exc


def connect_configuration(ctx: TaskContext, config: Mapping[str, Any], *, name: str = "effective") -> None:
    """Attach a minimal configuration snapshot to ClearML task."""
    if ctx.task is None:
        return
    connector = getattr(ctx.task, "connect_configuration", None)
    if not callable(connector):
        raise PlatformAdapterError("ClearML Task.connect_configuration is not available.")
    try:
        connector(dict(config), name=name)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to connect configuration via ClearML: {exc}") from exc


def report_markdown(ctx: TaskContext, *, title: str, markdown: str) -> bool:
    """Publish markdown text to ClearML when reporting is available."""
    if ctx.task is None:
        return False
    if not markdown:
        return False
    getter = getattr(ctx.task, "get_logger", None)
    if not callable(getter):
        return False
    try:
        logger = getter()
    except Exception:
        return False
    if logger is None:
        return False
    reporter = getattr(logger, "report_text", None)
    if not callable(reporter):
        return False
    try:
        payload = markdown.strip()
        if title:
            payload = f"# {title}\n\n{payload}"
        reporter(payload, print_console=False)
        return True
    except Exception:
        return False


def add_task_tags(ctx: TaskContext, tags: Iterable[str]) -> None:
    """Add tags to a ClearML task when enabled."""
    if ctx.task is None:
        return
    tag_list = _dedupe_tags(tags)
    if not tag_list:
        return
    task = ctx.task
    adder = getattr(task, "add_tags", None)
    if callable(adder):
        try:
            adder(tag_list)
            return
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to add task tags via ClearML: {exc}") from exc
    getter = getattr(task, "get_tags", None)
    setter = getattr(task, "set_tags", None)
    if callable(setter):
        existing: list[str] = []
        if callable(getter):
            try:
                current = getter() or []
                if isinstance(current, (str, bytes)):
                    existing = [str(current)]
                elif isinstance(current, Iterable):
                    existing = [str(item) for item in current]
            except Exception:
                existing = []
        merged = _dedupe_tags([*existing, *tag_list])
        try:
            setter(merged)
            return
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to set task tags via ClearML: {exc}") from exc
    raise PlatformAdapterError("ClearML task does not support tag updates.")


def register_model_artifact(
    ctx: TaskContext,
    *,
    model_path: Path,
    model_name: str,
    tags: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    comment: str | None = None,
    framework: str | None = None,
) -> str:
    """Register a model artifact in ClearML model registry and tag it."""
    if ctx.task is None:
        raise PlatformAdapterError("ClearML is disabled; cannot register model.")
    try:
        from clearml import OutputModel  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.OutputModel is required for model promotion.") from exc

    model_path = Path(model_path).expanduser().resolve()
    if not model_path.exists():
        raise PlatformAdapterError(f"Model file does not exist: {model_path}")

    try:
        output_model = OutputModel(
            task=ctx.task,
            name=str(model_name),
            tags=_dedupe_tags(tags or []),
            comment=comment,
            framework=framework,
        )
        output_model.update_weights(
            weights_filename=str(model_path),
            auto_delete_file=False,
            async_enable=False,
        )
        if metadata:
            for key, value in metadata.items():
                if value is None:
                    continue
                if isinstance(value, (dict, list, tuple)):
                    text = json.dumps(value, ensure_ascii=True)
                else:
                    text = str(value)
                if not text:
                    continue
                output_model.set_metadata(str(key), text)
        return str(output_model.id)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to register model via ClearML: {exc}") from exc


def register_promoted_model(
    ctx: TaskContext,
    *,
    model_path: Path,
    model_name: str,
    tags: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    comment: str | None = None,
    framework: str | None = None,
) -> str:
    """Register a promoted model artifact in ClearML model registry and tag it."""
    return register_model_artifact(
        ctx,
        model_path=model_path,
        model_name=model_name,
        tags=tags,
        metadata=metadata,
        comment=comment,
        framework=framework,
    )


def get_clearml_model_local_copy(model_id: str) -> Path:
    """Download a ClearML registry model artifact and return the local path."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for registry model downloads.") from exc
    try:
        model = Model(model_id=str(model_id))
        local_path = model.get_local_copy(raise_on_error=True)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to download ClearML model {model_id}: {exc}") from exc
    if not local_path:
        raise PlatformAdapterError(f"ClearML model {model_id} did not return a local copy path.")
    path = Path(local_path)
    if not path.exists():
        raise PlatformAdapterError(f"ClearML model local copy does not exist: {path}")
    return path.resolve()


def resolve_registry_model_bundle_by_stage(
    *,
    stage: str,
    usecase_id: str | None = None,
) -> tuple[str, Path]:
    """Resolve a ClearML registry model bundle by stage tags."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for registry queries.") from exc
    tags = ["__$all", f"stage:{stage}"]
    if usecase_id:
        tags.append(f"usecase:{usecase_id}")
    try:
        models = Model.query_models(
            tags=tags,
            only_published=False,
            include_archived=True,
            max_results=1,
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to query ClearML registry for stage {stage}: {exc}") from exc
    if not models:
        suffix = f" usecase={usecase_id}" if usecase_id else ""
        raise PlatformAdapterError(
            f"No ClearML registry model found for stage={stage}.{suffix}"
        )
    model = models[0]
    model_id = getattr(model, "id", None) or getattr(model, "model_id", None)
    model_id_str = str(model_id) if model_id is not None else "unknown"
    try:
        local_path = model.get_local_copy(raise_on_error=True)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to download ClearML model {model_id_str}: {exc}") from exc
    if not local_path:
        raise PlatformAdapterError(
            f"ClearML model {model_id_str} did not return a local copy path."
        )
    path = Path(local_path)
    if not path.exists():
        raise PlatformAdapterError(f"ClearML model local copy does not exist: {path}")
    return model_id_str, path.resolve()


def _model_tags(model: Any) -> list[str]:
    tags = getattr(model, "tags", None)
    if tags is None:
        return []
    if isinstance(tags, (str, bytes)):
        return [str(tags)]
    try:
        return [str(item) for item in tags]
    except Exception:
        return []


def _set_model_tags(model: Any, tags: Iterable[str]) -> None:
    try:
        model.tags = list(tags)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to update model tags via ClearML: {exc}") from exc


def _strip_tag_prefixes(tags: Iterable[str], prefixes: Iterable[str]) -> list[str]:
    prefix_list = [str(prefix) for prefix in prefixes if prefix is not None]
    if not prefix_list:
        return [str(tag) for tag in tags if tag is not None]
    cleaned: list[str] = []
    for tag in tags:
        if tag is None:
            continue
        text = str(tag)
        if any(text.startswith(prefix) for prefix in prefix_list):
            continue
        cleaned.append(text)
    return cleaned


def update_registry_model_tags(
    *,
    model_id: str,
    add_tags: Iterable[str] | None = None,
    remove_prefixes: Iterable[str] | None = None,
) -> list[str]:
    """Update tags on a ClearML registry model and return the final tags."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for registry tag updates.") from exc
    model = Model(model_id=str(model_id))
    tags = _model_tags(model)
    if remove_prefixes:
        tags = _strip_tag_prefixes(tags, remove_prefixes)
    if add_tags:
        tags = _dedupe_tags([*tags, *list(add_tags)])
    _set_model_tags(model, tags)
    return tags


def update_recommended_registry_model_tags(
    *,
    usecase_id: str,
    processed_dataset_id: str,
    recommended_model_id: str,
    tags_to_add: Iterable[str],
    remove_prefixes: Iterable[str],
) -> dict[str, Any]:
    """Mark the recommended model and clear old recommendation tags for the same dataset."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for registry queries.") from exc
    base_tags = ["__$all", f"usecase:{usecase_id}", f"dataset:{processed_dataset_id}"]
    try:
        models = Model.query_models(
            tags=base_tags,
            only_published=False,
            include_archived=True,
            max_results=200,
        )
    except Exception as exc:
        raise PlatformAdapterError(
            f"Failed to query ClearML registry for dataset={processed_dataset_id}: {exc}"
        ) from exc
    updated = 0
    for model in models:
        model_id = getattr(model, "id", None) or getattr(model, "model_id", None)
        model_id_str = str(model_id) if model_id is not None else ""
        tags = _strip_tag_prefixes(_model_tags(model), remove_prefixes)
        if model_id_str == recommended_model_id:
            tags = _dedupe_tags([*tags, *list(tags_to_add)])
        _set_model_tags(model, tags)
        updated += 1
    return {"updated_models": updated, "matched_models": len(models)}


def update_recommended_registry_model_tags_multi(
    *,
    usecase_id: str,
    processed_dataset_id: str,
    split_hash: str | None = None,
    recipe_hash: str | None = None,
    recommendations: Iterable[tuple[str, Iterable[str], Mapping[str, Any] | None]],
    remove_prefixes: Iterable[str],
) -> dict[str, Any]:
    """Update recommendation tags for multiple models (latest-only per dataset)."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for registry queries.") from exc
    rec_map = {
        str(model_id): {"tags": list(tags), "metadata": metadata or {}}
        for model_id, tags, metadata in recommendations
        if model_id
    }
    base_tags = ["__$all", f"usecase:{usecase_id}", f"dataset:{processed_dataset_id}"]
    if split_hash:
        base_tags.append(f"split:{split_hash}")
    if recipe_hash:
        base_tags.append(f"recipe:{recipe_hash}")
    try:
        models = Model.query_models(
            tags=base_tags,
            only_published=False,
            include_archived=True,
            max_results=200,
        )
    except Exception as exc:
        raise PlatformAdapterError(
            f"Failed to query ClearML registry for dataset={processed_dataset_id}: {exc}"
        ) from exc
    updated = 0
    for model in models:
        model_id = getattr(model, "id", None) or getattr(model, "model_id", None)
        model_id_str = str(model_id) if model_id is not None else ""
        tags = _strip_tag_prefixes(_model_tags(model), remove_prefixes)
        if model_id_str in rec_map:
            payload = rec_map[model_id_str]
            tags = _dedupe_tags([*tags, *payload.get("tags", [])])
            metadata = payload.get("metadata") or {}
            if metadata:
                _update_model_metadata(model, metadata)
        _set_model_tags(model, tags)
        updated += 1
    return {
        "updated_models": updated,
        "matched_models": len(models),
        "recommended_models": len(rec_map),
    }

def _update_model_metadata(model: Any, metadata: Mapping[str, Any]) -> None:
    setter = getattr(model, "set_metadata", None)
    if not callable(setter):
        return
    for key, value in metadata.items():
        if value is None:
            continue
        try:
            setter(str(key), str(value))
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to update model metadata via ClearML: {exc}") from exc


def _model_snapshot(model: Any | None) -> dict[str, Any] | None:
    if model is None:
        return None
    return {
        "registry_model_id": getattr(model, "id", None),
        "name": getattr(model, "name", None),
        "tags": _model_tags(model),
    }


def rollback_registry_stage(
    *,
    usecase_id: str,
    stage: str,
    target_model_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Rollback ClearML model registry stage to previous production (best-effort)."""
    try:
        from clearml import Model  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml.Model is required for model registry rollback.") from exc

    tags = ["__$all", f"usecase:{usecase_id}", f"stage:{stage}"]
    models = Model.query_models(
        tags=tags,
        only_published=False,
        include_archived=True,
        max_results=20,
    )
    current = models[0] if models else None
    target = None
    if target_model_id:
        target = Model(model_id=str(target_model_id))
    elif len(models) > 1:
        target = models[1]

    if target is None:
        raise PlatformAdapterError("No previous model found for rollback.")

    target_tags = _dedupe_tags(
        [*_model_tags(target), f"usecase:{usecase_id}", f"stage:{stage}", "rollback:true"]
    )
    _set_model_tags(target, target_tags)
    _update_model_metadata(
        target,
        {
            "promotion_stage": stage,
            "rollback_reason": reason,
            "rollback_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )

    if current is not None and getattr(current, "id", None) != getattr(target, "id", None):
        current_tags = [tag for tag in _model_tags(current) if tag != f"stage:{stage}"]
        _set_model_tags(current, _dedupe_tags(current_tags))

    return {"before": _model_snapshot(current), "after": _model_snapshot(target)}


def _get_clearml_task(task_id: str) -> Any:
    cached = _CLEARML_TASK_CACHE.get(task_id)
    if cached is not None:
        return cached
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required for task artifact retrieval.") from exc
    try:
        task = ClearMLTask.get_task(task_id=str(task_id))
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to load ClearML task: {task_id}") from exc
    _CLEARML_TASK_CACHE[task_id] = task
    return task


def clearml_task_exists(task_id: str) -> bool:
    _get_clearml_task(task_id)
    return True


def create_clearml_task(
    *,
    project_name: str,
    task_name: str,
    module: str | None = None,
    script: str | None = None,
    args: Iterable[str] | None = None,
    repo: str | None = None,
    branch: str | None = None,
    working_dir: str | None = None,
    task_type: str | None = None,
    tags: Iterable[str] | None = None,
    properties: Mapping[str, Any] | None = None,
    requirements: Iterable[str] | None = None,
) -> str:
    if module and script:
        raise PlatformAdapterError("Specify either module or script for ClearML task creation.")
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required to create ClearML tasks.") from exc
    try:
        task = ClearMLTask.create(
            project_name=str(project_name),
            task_name=str(task_name),
            task_type=task_type,
            repo=repo,
            branch=branch,
            script=script,
            working_directory=working_dir,
            module=module,
            argparse_args=list(args) if args else None,
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to create ClearML task: {exc}") from exc
    if tags:
        tag_list = _dedupe_tags(tags)
        if tag_list:
            try:
                task.add_tags(tag_list)
            except Exception as exc:
                raise PlatformAdapterError(f"Failed to set task tags via ClearML: {exc}") from exc
    if properties:
        setter = getattr(task, "set_user_properties", None)
        if callable(setter):
            normalized = {str(key): "" if value is None else str(value) for key, value in properties.items()}
            try:
                setter(*normalized.items())
            except Exception as exc:
                raise PlatformAdapterError(f"Failed to set task properties via ClearML: {exc}") from exc
    if requirements:
        setter = getattr(task, "set_packages", None)
        if not callable(setter):
            raise PlatformAdapterError("ClearML Task.set_packages is not available.")
        normalized = _normalize_requirement_lines(requirements)
        if normalized:
            try:
                setter(normalized)
            except Exception as exc:
                raise PlatformAdapterError(f"Failed to set task requirements via ClearML: {exc}") from exc
    task_id = getattr(task, "id", None)
    if not task_id:
        raise PlatformAdapterError("ClearML task id is missing after creation.")
    return str(task_id)


def list_clearml_tasks_by_tags(
    tags: Iterable[str],
    *,
    project_name: str | None = None,
    task_name: str | None = None,
    allow_archived: bool = True,
    order_by: Iterable[str] | None = None,
) -> list[Any]:
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required for ClearML task queries.") from exc
    tag_list = _dedupe_tags(tags)
    if not tag_list:
        raise PlatformAdapterError("tags are required to query ClearML tasks.")
    task_filter = {"order_by": list(order_by) if order_by else ["-last_update"]}
    try:
        tasks = ClearMLTask.get_tasks(
            project_name=project_name,
            task_name=task_name,
            tags=tag_list,
            allow_archived=allow_archived,
            task_filter=task_filter,
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to query ClearML tasks by tags: {exc}") from exc
    required = set(tag_list)
    filtered: list[Any] = []
    for task in list(tasks or []):
        task_tags = set(_task_tags(task))
        if required.issubset(task_tags):
            filtered.append(task)
    return filtered


def clearml_task_id(task: Any) -> str | None:
    task_id = getattr(task, "id", None) or getattr(task, "task_id", None)
    return str(task_id) if task_id else None


def clearml_task_tags(task: Any) -> list[str]:
    return _dedupe_tags(_task_tags(task))


def clearml_task_script(task: Any) -> dict[str, Any]:
    return _task_script(task)


def clearml_task_status_from_obj(task: Any) -> str | None:
    status = getattr(task, "status", None)
    if status:
        return str(status)
    getter = getattr(task, "get_status", None)
    if callable(getter):
        try:
            status = getter()
        except Exception:
            status = None
        if status:
            return str(status)
    return None


def find_clearml_task_id_by_tags(
    tags: Iterable[str],
    *,
    project_name: str | None = None,
    task_name: str | None = None,
    allow_archived: bool = True,
) -> str | None:
    """Resolve the most recently updated ClearML task id matching tags."""
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required for ClearML task queries.") from exc
    tag_list = _dedupe_tags(tags)
    if not tag_list:
        raise PlatformAdapterError("tags are required to query ClearML tasks.")
    try:
        tasks = ClearMLTask.get_tasks(
            project_name=project_name,
            task_name=task_name,
            tags=tag_list,
            allow_archived=allow_archived,
            task_filter={"order_by": ["-last_update"]},
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to query ClearML tasks by tags: {exc}") from exc
    if not tasks:
        return None
    task = tasks[0]
    task_id = getattr(task, "id", None) or getattr(task, "task_id", None)
    return str(task_id) if task_id else None


def _task_tags(task: Any) -> list[str]:
    getter = getattr(task, "get_tags", None)
    if callable(getter):
        try:
            tags = getter()
        except Exception:
            tags = None
        if tags is not None:
            if isinstance(tags, (list, tuple, set)):
                return [str(tag) for tag in tags if tag is not None]
            return [str(tags)]
    tags = getattr(task, "tags", None)
    if tags is not None:
        if isinstance(tags, (list, tuple, set)):
            return [str(tag) for tag in tags if tag is not None]
        return [str(tags)]
    data = getattr(task, "data", None)
    if isinstance(data, Mapping):
        tags = data.get("tags")
        if isinstance(tags, (list, tuple, set)):
            return [str(tag) for tag in tags if tag is not None]
    if data is not None:
        tags = getattr(data, "tags", None)
        if isinstance(tags, (list, tuple, set)):
            return [str(tag) for tag in tags if tag is not None]
    return []


def _task_script(task: Any) -> dict[str, Any]:
    script: dict[str, Any] = {}
    getter = getattr(task, "get_script", None)
    if callable(getter):
        try:
            script_value = getter()
        except Exception:
            script_value = None
        if isinstance(script_value, Mapping):
            script.update(dict(script_value))
    data = getattr(task, "data", None)
    script_obj = getattr(data, "script", None) if data is not None else None
    if script_obj is not None:
        fallback = {
            "repository": getattr(script_obj, "repository", None),
            "branch": getattr(script_obj, "branch", None),
            "entry_point": getattr(script_obj, "entry_point", None),
            "working_dir": getattr(script_obj, "working_dir", None),
            "version_num": getattr(script_obj, "version_num", None),
            "diff": getattr(script_obj, "diff", None),
        }
        for key, value in fallback.items():
            if key not in script or script[key] is None:
                script[key] = value
    return script


def _task_parameters(task: Any) -> dict[str, Any]:
    getter = getattr(task, "get_parameters", None)
    if callable(getter):
        try:
            params = getter()
        except Exception:
            params = None
        if isinstance(params, Mapping):
            return dict(params)
    getter = getattr(task, "get_parameters_as_dict", None)
    if callable(getter):
        try:
            params = getter()
        except Exception:
            params = None
        if isinstance(params, Mapping):
            flat: dict[str, Any] = {}
            for section, values in params.items():
                if not isinstance(values, Mapping):
                    continue
                for key, value in values.items():
                    flat[f"{section}/{key}"] = value
            return flat
    return {}


def _property_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if "value" in value:
            return value.get("value")
    return value


def _parse_task_args(args: Iterable[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in args:
        text = str(item).strip()
        if not text:
            continue
        if "=" not in text:
            raise PlatformAdapterError(f"override must be key=value: {text}")
        key, value = text.split("=", 1)
        parsed[str(key)] = str(value)
    return parsed


def get_clearml_task_tags(task_id: str) -> list[str]:
    task = _get_clearml_task(task_id)
    return _dedupe_tags(_task_tags(task))


def get_clearml_task_script(task_id: str) -> dict[str, Any]:
    task = _get_clearml_task(task_id)
    script = _task_script(task)
    return {
        "repository": script.get("repository"),
        "branch": script.get("branch"),
        "entry_point": script.get("entry_point"),
        "working_dir": script.get("working_dir"),
        "version_num": script.get("version_num"),
    }


def get_clearml_task_args(task_id: str) -> dict[str, str]:
    task = _get_clearml_task(task_id)
    params = _task_parameters(task)
    args: dict[str, str] = {}
    for key, value in params.items():
        if not isinstance(key, str) or not key.startswith("Args/"):
            continue
        args[key[5:]] = "" if value is None else str(value)
    return args


def clone_clearml_task(
    *,
    source_task_id: str | None = None,
    source_task: Any | None = None,
    task_name: str | None = None,
    parent_task_id: str | None = None,
) -> str:
    if not source_task_id and source_task is None:
        raise PlatformAdapterError("source_task_id or source_task is required to clone a task.")
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required to clone ClearML tasks.") from exc
    source = source_task if source_task is not None else str(source_task_id)
    try:
        cloned = ClearMLTask.clone(
            source_task=source,
            name=task_name,
            parent=parent_task_id,
        )
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to clone ClearML task: {exc}") from exc
    task_id = getattr(cloned, "id", None) or getattr(cloned, "task_id", None)
    if not task_id:
        raise PlatformAdapterError("Cloned ClearML task id is missing.")
    _CLEARML_TASK_CACHE[str(task_id)] = cloned
    return str(task_id)


def set_clearml_task_entry_point(task_id: str, entry_point: str) -> None:
    task = _get_clearml_task(task_id)
    script = _task_script(task)
    payload: dict[str, Any] = {}
    for key in ("repository", "branch", "working_dir", "version_num"):
        value = script.get(key)
        if value is not None:
            payload[key] = value
    payload["entry_point"] = entry_point
    _set_clearml_task_script(task, payload)


def set_clearml_task_parameters(
    task_id: str,
    parameters: Mapping[str, Any],
    *,
    section: str = "Args",
) -> bool:
    if not parameters:
        return False
    task = _get_clearml_task(task_id)
    json_keys = {
        "infer.input_json",
        "infer.batch.inputs_json",
        "infer.validation.inputs_json",
        "infer.optimize.search_space",
    }
    normalized: dict[str, str] = {}
    for key, value in parameters.items():
        key_text = str(key)
        if value is None:
            normalized[key_text] = ""
            continue
        if key_text in json_keys and isinstance(value, (Mapping, SequenceABC)) and not isinstance(
            value, (str, bytes)
        ):
            try:
                normalized[key_text] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                continue
            except Exception:
                pass
        normalized[key_text] = str(value)
    getter = getattr(task, "get_parameters_as_dict", None)
    existing = None
    if callable(getter):
        try:
            existing = getter(cast=False)
        except Exception:
            existing = None
    payload: dict[str, Any] = {}
    if isinstance(existing, Mapping):
        payload.update(existing)
    section_values: dict[str, Any] = {}
    if isinstance(payload.get(section), Mapping):
        section_values.update(dict(payload.get(section)))
    section_values.update(normalized)
    payload[section] = section_values
    setter = getattr(task, "set_parameters_as_dict", None)
    if callable(setter):
        setter(payload)
        return True
    setter = getattr(task, "set_parameter", None)
    if callable(setter):
        for key, value in section_values.items():
            setter(f"{section}/{key}", value)
        return True
    raise PlatformAdapterError("ClearML Task.set_parameters_as_dict is not available.")


def enqueue_clearml_task(task_id: str, queue_name: str, *, force: bool = False) -> None:
    if not queue_name:
        raise PlatformAdapterError("queue_name is required to enqueue a ClearML task.")
    try:
        from clearml import Task as ClearMLTask  # type: ignore
    except Exception as exc:
        raise PlatformAdapterError("clearml is required to enqueue ClearML tasks.") from exc
    try:
        ClearMLTask.enqueue(task=str(task_id), queue_name=str(queue_name), force=bool(force))
    except TypeError:
        try:
            ClearMLTask.enqueue(task_id=str(task_id), queue_name=str(queue_name), force=bool(force))
        except TypeError:
            ClearMLTask.enqueue(str(task_id), queue_name=str(queue_name))
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to enqueue ClearML task: {exc}") from exc


def get_clearml_task_status(task_id: str) -> str | None:
    task = _get_clearml_task(task_id)
    status = getattr(task, "status", None)
    if status:
        return str(status)
    getter = getattr(task, "get_status", None)
    if callable(getter):
        try:
            status = getter()
        except Exception:
            status = None
        if status:
            return str(status)
    return None


def ensure_clearml_task_tags(task_id: str, tags: Iterable[str]) -> bool:
    desired = _dedupe_tags(tags)
    if not desired:
        return False
    task = _get_clearml_task(task_id)
    existing = set(_task_tags(task))
    missing = [tag for tag in desired if tag not in existing]
    if not missing:
        return False
    adder = getattr(task, "add_tags", None)
    if not callable(adder):
        raise PlatformAdapterError("ClearML Task.add_tags is not available.")
    adder(missing)
    return True


def update_clearml_task_tags(
    task_id: str,
    *,
    add: Iterable[str] | None = None,
    remove: Iterable[str] | None = None,
) -> bool:
    add_list = _dedupe_tags(add or [])
    remove_set = set(_dedupe_tags(remove or []))
    if not add_list and not remove_set:
        return False
    task = _get_clearml_task(task_id)
    existing = _task_tags(task)
    updated = [tag for tag in existing if tag not in remove_set]
    updated = _dedupe_tags([*updated, *add_list])
    if updated == existing:
        return False
    setter = getattr(task, "set_tags", None)
    if callable(setter):
        setter(updated)
        return True
    if remove_set:
        raise PlatformAdapterError("ClearML Task.set_tags is not available for tag removal.")
    adder = getattr(task, "add_tags", None)
    if callable(adder):
        adder([tag for tag in add_list if tag not in existing])
        return True
    raise PlatformAdapterError("ClearML Task tag update is not available.")


def ensure_clearml_task_requirements(task_id: str, requirements: Iterable[str]) -> bool:
    desired = _normalize_requirement_lines(requirements)
    if not desired:
        return False
    task = _get_clearml_task(task_id)
    getter = getattr(task, "get_requirements", None)
    if not callable(getter):
        raise PlatformAdapterError("ClearML Task.get_requirements is not available.")
    try:
        existing = getter()
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to read task requirements via ClearML: {exc}") from exc
    existing_pip = existing.get("pip") if isinstance(existing, Mapping) else None
    if _normalize_requirement_lines(existing_pip) == desired:
        return False
    setter = getattr(task, "set_packages", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_packages is not available.")
    try:
        setter(desired)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to set task requirements via ClearML: {exc}") from exc
    return True


def ensure_clearml_task_properties(task_id: str, properties: Mapping[str, Any]) -> bool:
    if not properties:
        return False
    task = _get_clearml_task(task_id)
    existing = _existing_user_properties(task)
    updates: dict[str, Any] = {}
    for key, value in properties.items():
        expected = "" if value is None else str(value)
        current = _property_value(existing.get(str(key)))
        if current is None or str(current) != expected:
            updates[str(key)] = expected
    if not updates:
        return False
    setter = getattr(task, "set_user_properties", None)
    if not callable(setter):
        raise PlatformAdapterError("ClearML Task.set_user_properties is not available.")
    setter(*updates.items())
    return True


def ensure_clearml_task_args(task_id: str, args: Iterable[str]) -> bool:
    desired = _parse_task_args(args)
    if not desired:
        return False
    task = _get_clearml_task(task_id)
    params = _task_parameters(task)
    existing_args: dict[str, str] = {}
    for key, value in params.items():
        if isinstance(key, str) and key.startswith("Args/"):
            existing_args[key[5:]] = "" if value is None else str(value)
    updates: dict[str, str] = {}
    for key, value in desired.items():
        if existing_args.get(key) != value:
            updates[key] = value
    if not updates:
        return False
    updated_params = dict(params)
    for key, value in updates.items():
        updated_params[f"Args/{key}"] = value
    setter = getattr(task, "set_parameters", None)
    if callable(setter):
        setter(updated_params)
        return True
    setter = getattr(task, "set_parameters_as_dict", None)
    if callable(setter):
        merged = {**existing_args, **updates}
        setter({"Args": merged})
        return True
    raise PlatformAdapterError("ClearML Task.set_parameters is not available.")


def reset_clearml_task_args(task_id: str, args: Iterable[str]) -> bool:
    desired = _parse_task_args(args)
    task = _get_clearml_task(task_id)
    normalized = {str(key): "" if value is None else str(value) for key, value in desired.items()}
    getter = getattr(task, "get_parameters_as_dict", None)
    if callable(getter):
        try:
            params = getter(cast=False)
        except Exception:
            params = None
        if isinstance(params, Mapping):
            params = dict(params)
            params["Args"] = dict(normalized)
            setter = getattr(task, "set_parameters_as_dict", None)
            if callable(setter):
                setter(params)
                return True
    params = _task_parameters(task)
    updated = {k: v for k, v in params.items() if not (isinstance(k, str) and k.startswith("Args/"))}
    for key, value in normalized.items():
        updated[f"Args/{key}"] = value
    setter = getattr(task, "set_parameters", None)
    if callable(setter):
        setter(updated)
        return True
    setter = getattr(task, "set_parameters_as_dict", None)
    if callable(setter):
        setter({"Args": dict(normalized)})
        return True
    raise PlatformAdapterError("ClearML Task.set_parameters is not available.")


def apply_clearml_task_overrides(target: Any, overrides: Iterable[str]) -> bool:
    desired = _parse_task_args(overrides)
    if not desired:
        return False
    task = _resolve_clearml_task(target)
    return _apply_clearml_task_args(task, desired)


def ensure_clearml_task_script(
    task_id: str,
    *,
    repo: str | None,
    branch: str | None,
    entry_point: str | None,
    working_dir: str | None,
    version_num: str | None = None,
    diff: str | None = None,
) -> bool:
    if (
        repo is None
        and branch is None
        and entry_point is None
        and working_dir is None
        and version_num is None
        and diff is None
    ):
        return False
    task = _get_clearml_task(task_id)
    current = _task_script(task)
    changed = False
    if repo is not None and str(current.get("repository") or "") != str(repo):
        changed = True
    if branch is not None and str(current.get("branch") or "") != str(branch):
        changed = True
    if entry_point is not None and str(current.get("entry_point") or "") != str(entry_point):
        changed = True
    if working_dir is not None and str(current.get("working_dir") or "") != str(working_dir):
        changed = True
    if version_num is not None and str(current.get("version_num") or "") != str(version_num):
        changed = True
    if diff is not None and str(current.get("diff") or "") != str(diff):
        changed = True
    if not changed:
        return False
    payload: dict[str, Any] = {
        "repository": repo,
        "branch": branch,
        "working_dir": working_dir,
        "entry_point": entry_point,
    }
    if version_num is not None:
        payload["version_num"] = version_num
    if diff is not None:
        payload["diff"] = diff
    _set_clearml_task_script(task, payload)
    return True


def _resolve_task_artifact(task: Any, artifact_name: str) -> Any | None:
    artifacts = getattr(task, "artifacts", None)
    if isinstance(artifacts, Mapping):
        if artifact_name in artifacts:
            return artifacts[artifact_name]
    elif artifacts is not None and not isinstance(artifacts, (str, bytes)):
        try:
            for item in artifacts:
                if isinstance(item, Mapping):
                    key = item.get("key") or item.get("name")
                    if key == artifact_name:
                        return item
                else:
                    key = getattr(item, "key", None) or getattr(item, "name", None)
                    if key == artifact_name:
                        return item
        except Exception:
            pass
    getter = getattr(task, "get_artifact", None)
    if callable(getter):
        try:
            return getter(artifact_name)
        except Exception:
            return None
    return None


def _artifact_local_copy(artifact: Any) -> str | None:
    if artifact is None:
        return None
    if isinstance(artifact, Path):
        return str(artifact)
    if isinstance(artifact, str):
        return artifact
    getter = getattr(artifact, "get_local_copy", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            return None
    if isinstance(artifact, Mapping):
        for key in ("local_copy", "local_path", "path", "artifact_local_path"):
            value = artifact.get(key)
            if value:
                return str(value)
    return None


def get_task_artifact_local_copy(cfg: Any, task_id: str, artifact_name: str) -> Path:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot fetch task artifacts.")
    _apply_clearml_files_host_substitution()
    task = _get_clearml_task(task_id)
    artifact = _resolve_task_artifact(task, artifact_name)
    local_path = _artifact_local_copy(artifact)
    if not local_path:
        uri = None
        if isinstance(artifact, Mapping):
            uri = artifact.get("uri") or artifact.get("url")
        else:
            uri = getattr(artifact, "uri", None) or getattr(artifact, "url", None)
        if uri:
            try:
                from clearml.backend_api import Session  # type: ignore
            except Exception:
                Session = None
            try:
                import requests  # type: ignore
            except Exception:
                requests = None
            if Session is not None and requests is not None:
                try:
                    session = Session()
                    files_host = os.getenv("CLEARML_FILES_HOST") or session.config.get("api.files_server")
                    if files_host:
                        normalized = _normalize_files_host(files_host)
                        if normalized:
                            parsed = urlparse(uri)
                            if parsed.hostname in {"host.docker.internal", "clearml-fileserver"}:
                                uri = uri.replace(f"{parsed.scheme}://{parsed.netloc}", normalized)
                    creds = session.config.get("api.credentials")
                    token_resp = session.send_request(
                        service="auth",
                        action="login",
                        json={"access_key": creds["access_key"], "secret_key": creds["secret_key"]},
                    )
                    token = token_resp.json()["data"]["token"]
                    headers = {"Authorization": f"Bearer {token}"}
                    response = requests.get(uri, headers=headers, timeout=30)
                    response.raise_for_status()
                    target_dir = Path("/tmp/clearml_artifacts") / task_id
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_path = target_dir / artifact_name
                    target_path.write_bytes(response.content)
                    local_path = str(target_path)
                except Exception:
                    local_path = None
        if not local_path:
            raise PlatformAdapterError(
                f"Artifact {artifact_name} not found on ClearML task {task_id}."
            )
    path = Path(local_path)
    if not path.exists():
        raise PlatformAdapterError(
            f"Artifact {artifact_name} local copy does not exist: {path}"
        )
    return path


def resolve_clearml_task_url(cfg: Any, task_id: str) -> str | None:
    """Resolve a ClearML task URL when possible; returns None when unavailable."""
    if not is_clearml_enabled(cfg) or not task_id:
        return None
    try:
        task = _get_clearml_task(task_id)
    except Exception:
        return None
    for getter_name in ("get_output_log_web_page", "get_task_output_log_web_page"):
        getter = getattr(task, getter_name, None)
        if callable(getter):
            try:
                url = getter()
            except Exception:
                url = None
            if url:
                return str(url)
    url = getattr(task, "output_log_web_page", None)
    if url:
        return str(url)
    return None


def write_manifest(ctx: TaskContext, manifest: dict[str, Any]) -> Path:
    """manifest.json を保存。

    本来は platform の manifest builder（P201〜P204）を使うべき。
    ここは Codex が platform 実装に合わせて置き換える。
    """
    try:
        from ml_platform.artifacts import write_manifest as platform_write_manifest  # type: ignore
    except Exception as exc:
        if ctx.task is not None:
            raise PlatformAdapterError("ml_platform.artifacts.write_manifest not available.") from exc
        platform_write_manifest = None
    if platform_write_manifest is not None:
        try:
            return platform_write_manifest(
                manifest,
                output_dir=ctx.output_dir,
                task=ctx.task,
                filename="manifest.json",
            )
        except Exception as exc:
            raise PlatformAdapterError(f"Failed to write manifest via ml_platform: {exc}") from exc
    path = ctx.output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _connect_dataset_task_sections(
    dataset: Any,
    sections: Mapping[str, Mapping[str, Any]] | None,
    order: Iterable[str] | None,
) -> None:
    if not sections:
        return
    task = getattr(dataset, "_task", None)
    if task is None:
        return
    connector = getattr(task, "connect", None)
    if not callable(connector):
        return

    def _connect(name: str, payload: Mapping[str, Any]) -> None:
        cleaned = {key: value for key, value in payload.items() if value is not None}
        if not cleaned:
            return
        try:
            connector(dict(cleaned), name=name)
        except Exception as exc:
            print(
                f"[warn] Failed to connect dataset HyperParameters ({name}): {exc}",
                file=sys.stderr,
            )

    seen: set[str] = set()
    if order:
        for name in order:
            payload = sections.get(name)
            if not payload:
                continue
            _connect(name, payload)
            seen.add(name)
    for name, payload in sections.items():
        if name in seen:
            continue
        _connect(name, payload)


def register_dataset(
    cfg: Any,
    *,
    dataset_path: Path,
    dataset_name: str,
    dataset_project: str | None = None,
    dataset_tags: Optional[Iterable[str]] = None,
    dataset_version: str | None = None,
    description: str | None = None,
    parent_dataset_ids: Optional[Iterable[str]] = None,
    task_sections: Optional[Mapping[str, Mapping[str, Any]]] = None,
    task_section_order: Optional[Iterable[str]] = None,
) -> str:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot register dataset.")
    ClearMLDataset = _load_clearml_dataset(clearml_enabled=True)
    try:
        parents = [str(parent) for parent in (parent_dataset_ids or []) if parent]
        dataset = ClearMLDataset.create(
            dataset_name=dataset_name,
            dataset_project=dataset_project,
            dataset_tags=list(dataset_tags) if dataset_tags else None,
            dataset_version=dataset_version,
            description=description,
            parent_datasets=parents or None,
        )
        _connect_dataset_task_sections(dataset, task_sections, task_section_order)
        dataset.add_files(path=str(dataset_path))
        dataset.upload()
        dataset.finalize()
        return str(dataset.id)
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to register dataset via ClearML: {exc}") from exc


def get_dataset_local_copy(cfg: Any, dataset_id: str) -> Path:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot fetch dataset.")
    ClearMLDataset = _load_clearml_dataset(clearml_enabled=True)
    _apply_clearml_files_host_substitution()
    try:
        dataset = ClearMLDataset.get(dataset_id=str(dataset_id))
        local_path = dataset.get_local_copy()
    except Exception as exc:
        _apply_clearml_files_host_substitution()
        try:
            dataset = ClearMLDataset.get(dataset_id=str(dataset_id))
            local_path = dataset.get_local_copy()
        except Exception as exc_retry:
            raise PlatformAdapterError(f"Failed to fetch dataset via ClearML: {exc_retry}") from exc_retry
    if not local_path:
        raise PlatformAdapterError("ClearML Dataset.get_local_copy returned an empty path.")
    return Path(local_path)


def get_dataset_info(cfg: Any, dataset_id: str) -> dict[str, Any]:
    if not is_clearml_enabled(cfg):
        raise PlatformAdapterError("ClearML is disabled; cannot fetch dataset info.")
    ClearMLDataset = _load_clearml_dataset(clearml_enabled=True)
    try:
        dataset = ClearMLDataset.get(dataset_id=str(dataset_id))
    except Exception as exc:
        raise PlatformAdapterError(f"Failed to fetch dataset info via ClearML: {exc}") from exc
    info: dict[str, Any] = {"dataset_id": str(getattr(dataset, "id", dataset_id))}
    version = getattr(dataset, "version", None)
    if version is None:
        version = getattr(dataset, "dataset_version", None)
    if version is not None:
        info["dataset_version"] = str(version)
    name = getattr(dataset, "name", None)
    if name:
        info["dataset_name"] = str(name)
    project = getattr(dataset, "project", None)
    if project:
        info["dataset_project"] = str(project)
    return info


def _load_clearml_pipeline_utils(clearml_enabled: bool):
    try:
        from ml_platform.integrations.clearml import pipeline_utils as platform_pipeline_utils  # type: ignore
    except Exception as exc:
        if clearml_enabled:
            raise PlatformAdapterError(
                "ml_platform.integrations.clearml.pipeline_utils not available for ClearML runs."
            ) from exc
        return None
    return platform_pipeline_utils


def create_pipeline_controller(
    cfg: Any,
    *,
    name: str | None = None,
    tags: Iterable[str] | None = None,
    properties: Mapping[str, Any] | None = None,
    default_queue: str | None = None,
) -> Any:
    pipeline_utils = _load_clearml_pipeline_utils(clearml_enabled=True)
    if pipeline_utils is None:
        raise PlatformAdapterError("pipeline_utils is not available.")
    project_mode = str(_cfg_value(cfg, "run.clearml.pipeline.project_mode", "subproject")).lower()
    tag_pipeline_project = bool(_cfg_value(cfg, "run.clearml.pipeline.project_tag_pipeline", project_mode == "visible"))
    unhide_pipeline_project = bool(_cfg_value(cfg, "run.clearml.pipeline.project_unhide", project_mode == "visible"))
    controller_project = _cfg_value(cfg, "run.clearml.pipeline.project_name")
    if not controller_project:
        controller_project = _cfg_value(cfg, "run.clearml.project_name")
    if project_mode == "visible":
        try:
            from clearml.automation import PipelineController  # type: ignore
        except Exception:
            PipelineController = None
        if PipelineController is not None:
            PipelineController._pipeline_as_sub_project_cached = False
    elif project_mode == "subproject":
        try:
            from clearml.automation import PipelineController  # type: ignore
        except Exception:
            PipelineController = None
        if PipelineController is not None:
            PipelineController._pipeline_as_sub_project_cached = True
    tag_list: list[str] = []
    if tags:
        tag_list = [str(tag) for tag in tags if tag]
    if "pipeline" not in tag_list:
        tag_list.append("pipeline")
    controller = pipeline_utils.create_controller(
        cfg,
        name=name,
        project=str(controller_project) if controller_project else None,
        tags=tag_list,
        default_queue=default_queue,
    )
    try:
        if hasattr(controller, "_target_project"):
            controller._target_project = False
    except Exception:
        pass
    task = _resolve_clearml_task(controller)
    _apply_clearml_task_type(task, clearml_task_type_controller())
    _apply_clearml_system_tags(task, ["pipeline"])
    if tag_list:
        _apply_clearml_tags(task, tag_list)
    execution_project = _cfg_value(cfg, "run.clearml.project_name") or controller_project
    if execution_project:
        mover = getattr(task, "move_to_project", None)
        if callable(mover):
            try:
                current_project = None
                getter = getattr(task, "get_project_name", None)
                if callable(getter):
                    current_project = getter()
                if not current_project:
                    current_project = getattr(task, "project", None)
                if str(current_project or "") != str(execution_project):
                    mover(new_project_name=str(execution_project))
            except Exception:
                pass
    if tag_pipeline_project or execution_project:
        if execution_project:
            project_name = execution_project
        elif project_mode == "subproject":
            project_name = getattr(task, "project", None) or controller_project
        else:
            project_name = controller_project or getattr(task, "project", None)
        remove_tags = ["hidden"] if unhide_pipeline_project else []
        _ensure_clearml_project_system_tags(project_name, ["pipeline"], remove_tags=remove_tags)
    if properties:
        platform_clearml = _load_clearml_module(clearml_enabled=True)
        setter = getattr(platform_clearml, "set_user_properties", None)
        if setter is None:
            raise PlatformAdapterError("ml_platform.integrations.clearml.set_user_properties not found.")
        existing = _existing_user_properties(task)
        merged = {**existing, **dict(properties)}
        setter(task, merged)
    _apply_clearml_task_script_override(controller, cfg)
    _apply_clearml_pipeline_args(controller, cfg)
    _apply_clearml_task_requirements(
        _resolve_clearml_task(controller),
        _resolve_clearml_pipeline_requirements(cfg),
    )
    return controller


def pipeline_require_clearml_agent(queue_name: str | None = None) -> None:
    if os.getenv("CLEARML_TASK_ID") or os.getenv("TRAINS_TASK_ID"):
        return
    pipeline_utils = _load_clearml_pipeline_utils(clearml_enabled=True)
    if pipeline_utils is None:
        raise PlatformAdapterError("pipeline_utils is not available.")
    try:
        pipeline_utils.require_clearml_agent(queue_name)
    except RuntimeError as exc:
        print(f"[warn] {exc}", file=sys.stderr)


def pipeline_step_task_id_ref(step_name: str) -> str:
    pipeline_utils = _load_clearml_pipeline_utils(clearml_enabled=True)
    if pipeline_utils is None:
        raise PlatformAdapterError("pipeline_utils is not available.")
    return pipeline_utils.step_task_id_ref(step_name)
