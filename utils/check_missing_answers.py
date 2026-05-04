import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
ANSWERS_DIR = REPO_ROOT / "answers"
sys.path.insert(0, str(REPO_ROOT))

from common import Shared


def _normalized_model_name(model_name):
    return model_name.replace(":", "").replace("/", "")


def _extract_model_catalogue():
    return [
        model if isinstance(model, str) else model[0]
        for model in Shared.MODEL_CATALOGUE
    ]


def _get_prompts():
    return sorted(path.name for path in PROMPTS_DIR.iterdir() if path.is_file())


def _get_missing_prompts(model_name, prompts):
    normalized_name = _normalized_model_name(model_name)
    missing_prompts = []

    for prompt in prompts:
        answer_path = ANSWERS_DIR / f"{normalized_name}__{prompt}"
        if (not answer_path.exists()) or answer_path.stat().st_size == 0:
            missing_prompts.append(prompt)

    return missing_prompts


def main():
    prompts = _get_prompts()
    model_names = _extract_model_catalogue()
    models_with_missing_answers = []

    for model_name in model_names:
        missing_prompts = _get_missing_prompts(model_name, prompts)
        if missing_prompts:
            models_with_missing_answers.append(model_name)

    if not models_with_missing_answers:
        print("All models in Shared.MODEL_CATALOGUE have answers for every prompt.")
        return 0

    for model_name in models_with_missing_answers:
        print(model_name)

    return 1


if __name__ == "__main__":
    sys.exit(main())
