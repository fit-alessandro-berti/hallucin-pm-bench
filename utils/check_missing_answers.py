import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_PATH = REPO_ROOT / "common.py"
PROMPTS_DIR = REPO_ROOT / "prompts"
ANSWERS_DIR = REPO_ROOT / "answers"


def _normalized_model_name(model_name):
    return model_name.replace(":", "").replace("/", "")


def _extract_model_catalogue():
    source = COMMON_PATH.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(COMMON_PATH))

    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Shared":
            continue

        for child in node.body:
            if not isinstance(child, ast.Assign):
                continue

            for target in child.targets:
                if isinstance(target, ast.Name) and target.id == "MODEL_CATALOGUE":
                    return _extract_model_names(child.value)

    raise RuntimeError("Could not find Shared.MODEL_CATALOGUE in common.py")


def _extract_model_names(node):
    if not isinstance(node, (ast.List, ast.Tuple)):
        raise RuntimeError("Shared.MODEL_CATALOGUE is not a list or tuple literal")

    model_names = []

    for item in node.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            model_names.append(item.value)
            continue

        if isinstance(item, ast.Tuple) and item.elts:
            first = item.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                model_names.append(first.value)
                continue

        raise RuntimeError(f"Unsupported MODEL_CATALOGUE entry: {ast.dump(item, include_attributes=False)}")

    return model_names


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
