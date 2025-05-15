import os, time
from common import *


def respond_for_model(model_name, parameters=None):
    if parameters is None:
        parameters = {}

    m_name = model_name.replace(":", "").replace("/", "")
    base_model_name = parameters.get("base_model", model_name)

    for prompt in os.listdir("prompts"):
        prompt_content = open(os.path.join("prompts", prompt), encoding="utf-8").read() + parameters.get("add_prompt", "")
        answer_path = os.path.join("answers", m_name+"__"+prompt)

        if (not os.path.exists(answer_path)) or (os.path.getsize(answer_path) == 0):
            aa = time.time_ns()
            print("starting", model_name, prompt, answer_path)

            try:
                answer = get_response(prompt_content, base_model_name)

                if answer:
                    F = open(answer_path, "w", encoding="utf-8")
                    F.write(answer)
                    F.close()

                    bb = time.time_ns()
                    print("completed", round((bb-aa)/10**9, 3), model_name, prompt, answer_path)
            except Exception as e:
                print("except", model_name, prompt, answer_path, str(e))



if __name__ == "__main__":
    for model in ["openai/gpt-4.1",
                  "openai/gpt-4.1-mini",
                  "openai/gpt-4.1-nano",
                  "openai/gpt-4.5-preview",
                  ("qwen/qwen3-14b-nothink", {"base_model": "qwen/qwen3-14b", "add_prompt": " /no_think"}),
                  ("qwen/qwen3-14b-think", {"base_model": "qwen/qwen3-14b", "add_prompt": " /think"}),
                  "anthropic/claude-3.7-sonnet",
                  "x-ai/grok-3-beta",
                  "openai/o4-mini-high",
                  "openai/o4-mini",
                  "x-ai/grok-3-mini-beta",
                  "openai/chatgpt-4o-latest",
                  "anthropic/claude-3.7-sonnet:thinking",
                  "google/gemini-2.5-flash-preview",
                  "google/gemini-2.5-pro-preview",
                  "openai/o3-mini-high",
                  "openai/o3-mini",
                  "openai/o1",
                  ]:
        parameters = None if isinstance(model, str) else model[1]
        model_name = model if isinstance(model, str) else model[0]
        respond_for_model(model_name, parameters)
