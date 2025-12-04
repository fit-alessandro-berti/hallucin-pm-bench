import os
from results import *


def do_deletion(base_path, original_name):
    if not os.path.exists(base_path):
        raise Exception("base_path %s does not exists!" % (base_path))

    files = [x for x in os.listdir(base_path) if x.startswith(original_name)]

    for f in files:
        original_path = os.path.join(base_path, f)
        print(original_path)
        os.remove(original_path)


if __name__ == "__main__":
    original_name = "openrouterbert-nebulon-alpha_"

    if not original_name.endswith("_"):
        raise Exception("original_name must terminate with _")

    os.chdir("..")
    do_deletion("answers", original_name)
    do_deletion("evaluations", original_name)

    main("evaluations", "leaderboard.md", write_extra_stats=True)

