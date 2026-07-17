#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from file_utils import read_file_with_fallback


REPO_ROOT = Path(__file__).resolve().parent
MODELS_CONFIG_PATH = REPO_ROOT / "models.json"

PROVIDER_API_URLS = {
    "openrouter": "https://openrouter.ai/api/v1/",
    "openai": "https://api.openai.com/v1/",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "claude": "https://api.anthropic.com/v1/",
    "anthropic": "https://api.anthropic.com/v1/",
    "grok": "https://api.x.ai/v1/",
    "x-ai": "https://api.x.ai/v1/",
    "mistral": "https://api.mistral.ai/v1/",
    "deepinfra": "https://api.deepinfra.com/v1/openai/",
    "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/",
    "nvidia": "https://integrate.api.nvidia.com/v1/",
    "perplexity": "https://api.perplexity.ai/",
    "groq": "https://api.groq.com/openai/v1/",
}

PROVIDER_API_KEY_ENVS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "grok": "GROK_API_KEY",
    "x-ai": "GROK_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepinfra": "DEEPINFRA_API_KEY",
    "qwen": "QWEN_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "groq": "GROQ_API_KEY",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute hallucin-pm-bench for one target model.")
    parser.add_argument("model_name", help="Model alias to benchmark.")
    parser.add_argument("--provider", default="openrouter", help="Model provider. Defaults to openrouter.")
    parser.add_argument("--base-model", help="Underlying API model. Defaults to model_name.")
    parser.add_argument("--alias", help="Alias used inside the benchmark. Defaults to model_name.")
    parser.add_argument("--api-url", help="Override API URL.")
    parser.add_argument("--api-key-env", help="Environment variable containing the API key.")
    parser.add_argument("--api-key-file", help="Path to a file containing the API key.")
    parser.add_argument("--reasoning-effort", help="Optional reasoning effort.")
    parser.add_argument("--reasoning-enabled", action="store_true", help="Set payload.reasoning.enabled=true.")
    parser.add_argument("--thinking-tokens", type=int, help="Accepted for CLI compatibility; unused here.")
    parser.add_argument("--temperature", type=float, help="Optional sampling temperature.")
    parser.add_argument("--max-tokens", type=int, help="Optional max token cap.")
    parser.add_argument("--system-prompt", help="Accepted for CLI compatibility; unused here.")
    parser.add_argument("--add-prompt", help="Optional prompt suffix.")
    parser.add_argument("--payload-json", help="JSON object merged into the payload.")
    parser.add_argument("--tools-json", help="Accepted for CLI compatibility; unused here.")
    parser.add_argument("--config-json", help="Extra JSON object merged into the config.")
    parser.add_argument("--config-file", help="Path to a JSON file merged into the config.")
    parser.add_argument(
        "--disable-git-clean",
        action="store_true",
        help="Skip git clean during repository preflight. Disabled by default.",
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable for subprocess phases.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing them.")
    return parser


def merge_dicts(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def parse_json_object(raw: str | None, label: str) -> Dict[str, Any]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must decode to a JSON object.")
    return parsed


def load_runtime_config(args: argparse.Namespace) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    if args.config_file:
        file_config = json.loads(read_file_with_fallback(args.config_file))
        if not isinstance(file_config, dict):
            raise ValueError("config-file must contain a JSON object.")
        config = merge_dicts(config, file_config)
    config = merge_dicts(config, parse_json_object(args.config_json, "config-json"))
    if args.payload_json:
        config["payload"] = merge_dicts(config.get("payload", {}), parse_json_object(args.payload_json, "payload-json"))

    config.setdefault("provider", args.provider)
    config.setdefault("alias", args.alias or args.model_name)
    config.setdefault("base_model", args.base_model or args.model_name)
    config.setdefault("api_url", args.api_url or PROVIDER_API_URLS.get(config["provider"]))
    config.setdefault("api_key_env", args.api_key_env or PROVIDER_API_KEY_ENVS.get(config["provider"]))
    if args.api_key_file:
        config["api_key_file"] = args.api_key_file
    if args.reasoning_effort is not None:
        config.setdefault("payload", {})
        config["payload"]["reasoning_effort"] = args.reasoning_effort
    if args.reasoning_enabled:
        config.setdefault("payload", {})
        config["payload"].setdefault("reasoning", {})
        config["payload"]["reasoning"]["enabled"] = True
    if args.temperature is not None:
        config.setdefault("payload", {})
        config["payload"]["temperature"] = args.temperature
    if args.max_tokens is not None:
        config.setdefault("payload", {})
        config["payload"]["max_tokens"] = args.max_tokens
    if args.add_prompt is not None:
        config["add_prompt"] = args.add_prompt

    return config


def build_registration_entry(config: Dict[str, Any]) -> str | list[Any]:
    runtime_parameters: Dict[str, Any] = {}

    if config["base_model"] != config["alias"]:
        runtime_parameters["base_model"] = config["base_model"]
    if config.get("api_url"):
        runtime_parameters["api_url"] = config["api_url"]
    if config.get("api_key_env"):
        runtime_parameters["api_key_env"] = config["api_key_env"]
    if config.get("payload"):
        runtime_parameters["payload"] = config["payload"]
    if config.get("add_prompt"):
        runtime_parameters["add_prompt"] = config["add_prompt"]

    if not runtime_parameters:
        return config["alias"]
    return [config["alias"], runtime_parameters]


def ensure_model_registered(config: Dict[str, Any], dry_run: bool) -> None:
    models_config = json.loads(read_file_with_fallback(MODELS_CONFIG_PATH))

    model_catalogue = models_config.setdefault("model_catalogue", [])
    alias = config["alias"]
    for entry in model_catalogue:
        if entry == alias:
            return
        if isinstance(entry, list) and entry and entry[0] == alias:
            return

    model_catalogue.append(build_registration_entry(config))
    if dry_run:
        return

    with open(MODELS_CONFIG_PATH, "w", encoding="utf-8") as handler:
        json.dump(models_config, handler, indent=2)
        handler.write("\n")


def read_api_key(config: Dict[str, Any]) -> str | None:
    api_key_env = config.get("api_key_env")
    if api_key_env and os.environ.get(api_key_env):
        return os.environ[api_key_env]

    api_key_file = config.get("api_key_file")
    if api_key_file:
        candidate = Path(api_key_file)
        if not candidate.is_absolute():
            candidate = (REPO_ROOT / candidate).resolve()
        if candidate.exists():
            return read_file_with_fallback(candidate).strip()

    return None


def build_runtime_parameters(config: Dict[str, Any]) -> Dict[str, Any]:
    parameters: Dict[str, Any] = {}
    if config["base_model"] != config["alias"]:
        parameters["base_model"] = config["base_model"]
    if config.get("api_url"):
        parameters["api_url"] = config["api_url"]
    if config.get("api_key_env"):
        parameters["api_key_env"] = config["api_key_env"]
    if config.get("payload"):
        parameters["payload"] = config["payload"]
    if config.get("add_prompt"):
        parameters["add_prompt"] = config["add_prompt"]
    api_key = read_api_key(config)
    if api_key:
        parameters["api_key"] = api_key
    return parameters


def run_subprocess(command: list[str], cwd: Path, dry_run: bool) -> None:
    print("+", " ".join(command))
    if dry_run:
        return
    subprocess.run(command, cwd=str(cwd), check=True)


def sync_repository(dry_run: bool, disable_git_clean: bool = False) -> None:
    git_commands = [["git", "reset", "--hard", "HEAD"]]
    if disable_git_clean:
        print("# git clean disabled")
    else:
        git_commands.append(["git", "clean", "-x", "-f"])
    git_commands.append(["git", "pull"])
    for command in git_commands:
        run_subprocess(command, cwd=REPO_ROOT, dry_run=dry_run)


def publish_results(config: Dict[str, Any], dry_run: bool) -> None:
    if not (REPO_ROOT / ".git").exists():
        return

    commit_message = f"Update hallucin-pm-bench results for {config['alias']}"
    run_subprocess(["git", "add", "-A"], cwd=REPO_ROOT, dry_run=dry_run)
    if dry_run:
        run_subprocess(["git", "commit", "-m", commit_message], cwd=REPO_ROOT, dry_run=True)
        run_subprocess(["git", "push"], cwd=REPO_ROOT, dry_run=True)
        return

    diff_result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(REPO_ROOT), check=False)
    if diff_result.returncode == 0:
        print("No git changes to commit.")
        return
    if diff_result.returncode not in {0, 1}:
        diff_result.check_returncode()

    run_subprocess(["git", "commit", "-m", commit_message], cwd=REPO_ROOT, dry_run=False)
    run_subprocess(["git", "push"], cwd=REPO_ROOT, dry_run=False)


def execute_pipeline(config: Dict[str, Any], python_executable: str, dry_run: bool) -> None:
    if dry_run:
        print(f"Would execute hallucin-pm-bench for alias={config['alias']} base_model={config['base_model']}")
        return

    answer_module = importlib.import_module("answer")
    evaluation_module = importlib.import_module("evaluation")

    runtime_parameters = build_runtime_parameters(config)
    answer_module.respond_for_model(config["alias"], runtime_parameters)

    model_filter = evaluation_module._normalized_model_name(config["alias"])
    target_directory = evaluation_module.EVALUATIONS_DIR
    modified = True
    while modified:
        model_order, answer_groups = evaluation_module._build_evaluation_order(
            target_directory,
            model_filter=model_filter,
        )
        pending_answers = []
        for model_name in model_order:
            pending_answers.extend(
                evaluation_module._pending_answers_for_model(model_name, answer_groups, target_directory)
            )
        modified = evaluation_module._evaluate_answer_batch(
            pending_answers,
            evaluation_module.EVALUATING_MODEL_NAME,
            target_directory,
            True,
            {},
        ) if pending_answers else False

    run_subprocess([python_executable, "results.py"], cwd=REPO_ROOT, dry_run=False)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_runtime_config(args)
    sync_repository(args.dry_run, args.disable_git_clean)
    ensure_model_registered(config, args.dry_run)
    execute_pipeline(config, python_executable=args.python, dry_run=args.dry_run)
    publish_results(config, args.dry_run)


if __name__ == "__main__":
    main()
