import os, time
from common import *


def respond_for_model(model_name, parameters=None):
    if parameters is None:
        parameters = {}

    m_name = model_name.replace(":", "").replace("/", "")
    base_model_name = parameters.get("base_model", model_name)
    changed = False

    for prompt in os.listdir("prompts"):
        prompt_content = open(os.path.join("prompts", prompt), encoding="utf-8").read() + parameters.get("add_prompt", "")
        answer_path = os.path.join("answers", m_name+"__"+prompt)

        if (not os.path.exists(answer_path)) or (os.path.getsize(answer_path) == 0):
            aa = time.time_ns()
            print("starting", model_name, prompt, answer_path)

            try:
                answer = get_response(prompt_content, base_model_name, parameters=parameters)

                if answer:
                    F = open(answer_path, "w", encoding="utf-8")
                    F.write(answer)
                    F.close()

                    bb = time.time_ns()
                    print("completed", round((bb-aa)/10**9, 3), model_name, prompt, answer_path)
                    changed = True
            except Exception as e:
                print("except", model_name, prompt, answer_path, str(e))
    return changed

def main():
    changed = False
    for model in Shared.MODEL_CATALOGUE:
        parameters = None if isinstance(model, str) else model[1]
        model_name = model if isinstance(model, str) else model[0]
        changed = changed or respond_for_model(model_name, parameters)

    return changed


if __name__ == "__main__":
    changed = True
    while changed:
        changed = main()
        print("round finished")
