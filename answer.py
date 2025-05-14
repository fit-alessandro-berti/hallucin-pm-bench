import os
from common import *


def respond_for_model(model_name):
    m_name = model_name.replace(":", "").replace("/", "")

    for prompt in os.listdir("prompts"):
        prompt_content = open(os.path.join("prompts", prompt), encoding="utf-8").read()
        answer_path = os.path.join("answers", m_name+"__"+prompt)

        if (not os.path.exists(answer_path)) or (os.path.getsize(answer_path) == 0):
            print("starting", model_name, prompt, answer_path)

            try:
                answer = get_response(prompt_content, model_name)

                if answer:
                    F = open(answer_path, "w", encoding="utf-8")
                    F.write(answer)
                    F.close()

                    print("completed", model_name, prompt, answer_path)
            except Exception as e:
                print("except", model_name, prompt, answer_path, str(e))



if __name__ == "__main__":
    respond_for_model("openai/gpt-4.1-mini")
