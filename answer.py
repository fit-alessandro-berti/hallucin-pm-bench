import os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from common import *


MANUAL = False
MAX_THREADS = 50


def _respond_single_prompt(prompt, model_name, m_name, base_model_name, parameters):
    answer_path = os.path.join("answers", m_name + "__" + prompt)

    if os.path.exists(answer_path) and os.path.getsize(answer_path) > 0:
        return False

    prompt_content = open(os.path.join("prompts", prompt), encoding="utf-8").read() + parameters.get("add_prompt", "")

    aa = time.time_ns()
    print("starting", model_name, prompt, answer_path)

    try:
        is_completed = False

        if MANUAL:
            import pyperclip, subprocess
            pyperclip.copy(prompt_content)

            F = open(answer_path, "w")
            F.close()

            subprocess.run(["notepad.exe", answer_path])
            if os.path.getsize(answer_path) > 0:
                is_completed = True
        else:
            answer = get_response(prompt_content, base_model_name, parameters=parameters)

            if answer:
                F = open(answer_path, "w", encoding="utf-8")
                F.write(answer)
                F.close()
                is_completed = True

        bb = time.time_ns()
        if is_completed:
            print("completed", round((bb-aa)/10**9, 3), model_name, prompt, answer_path)
            return True
    except Exception as e:
        print("except", model_name, prompt, answer_path, str(e))
        time.sleep(20)

    return False


def respond_for_model(model_name, parameters=None):
    if parameters is None:
        parameters = {}

    m_name = model_name.replace(":", "").replace("/", "")
    base_model_name = parameters.get("base_model", model_name)
    changed = False

    if MANUAL:
        for prompt in os.listdir("prompts"):
            changed = _respond_single_prompt(prompt, model_name, m_name, base_model_name, parameters) or changed
        return changed

    futures = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for prompt in os.listdir("prompts"):
            answer_path = os.path.join("answers", m_name + "__" + prompt)

            if (not os.path.exists(answer_path)) or (os.path.getsize(answer_path) == 0):
                futures.append(executor.submit(
                    _respond_single_prompt,
                    prompt,
                    model_name,
                    m_name,
                    base_model_name,
                    parameters
                ))

        for future in as_completed(futures):
            try:
                changed = future.result() or changed
            except Exception as e:
                print("thread except", str(e))

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
