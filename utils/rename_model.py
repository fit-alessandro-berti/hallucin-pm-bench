import os
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from results import main as write_results


ORIGINAL_MODEL_NAME = "mistral-medium-3.5-thinkhigh"
TARGET_MODEL_NAME = "mistral-medium-3.5"
TARGET_FOLDERS = ("answers", "evaluations", "stats/self_evaluation")


def normalize_model_name(model_name):
    return model_name.replace(":", "").replace("/", "")


def model_prefix(model_name):
    return normalize_model_name(model_name) + "__"


def rename_model_files(base_path, original_model_name, target_model_name):
    if not os.path.exists(base_path):
        raise Exception("base_path %s does not exists!" % (base_path))

    original_prefix = model_prefix(original_model_name)
    target_prefix = model_prefix(target_model_name)
    files = sorted(x for x in os.listdir(base_path) if x.startswith(original_prefix))

    for file_name in files:
        original_path = os.path.join(base_path, file_name)
        target_name = target_prefix + file_name[len(original_prefix):]
        target_path = os.path.join(base_path, target_name)

        if os.path.exists(target_path):
            raise Exception("target file already exists: %s" % (target_path))

        print(original_path, "->", target_path)
        os.rename(original_path, target_path)

    return len(files)


def rename_model(original_model_name, target_model_name):
    if not original_model_name:
        raise Exception("ORIGINAL_MODEL_NAME must be set")
    if not target_model_name:
        raise Exception("TARGET_MODEL_NAME must be set")
    if normalize_model_name(original_model_name) == normalize_model_name(target_model_name):
        raise Exception("original and target model names normalize to the same value")

    os.chdir(REPO_ROOT)

    total = 0
    for base_path in TARGET_FOLDERS:
        total += rename_model_files(base_path, original_model_name, target_model_name)

    print("renamed", total, "files")
    write_results("evaluations", "leaderboard.md", write_extra_stats=True)


if __name__ == "__main__":
    rename_model(ORIGINAL_MODEL_NAME, TARGET_MODEL_NAME)
