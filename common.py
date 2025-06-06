import requests
import traceback
import json


class Shared:
    API_URL = "https://openrouter.ai/api/v1/"
    API_KEY = open("api_key.txt", "r").read().strip()

    MODEL_CATALOGUE = ["openai/gpt-4.1",
                  "openai/gpt-4.1-mini",
                  "openai/gpt-4.1-nano",
                  "openai/gpt-4.5-preview",
                  ("qwen/qwen3-14b-nothink", {"base_model": "qwen/qwen3-14b", "add_prompt": " /no_think"}),
                  ("qwen/qwen3-14b-think", {"base_model": "qwen/qwen3-14b", "add_prompt": " /think"}),
                  "anthropic/claude-3.7-sonnet", "anthropic/claude-3.5-sonnet",
                  "anthropic/claude-sonnet-4", "anthropic/claude-opus-4",
                  "x-ai/grok-3-beta",
                  "openai/o4-mini-high",
                  "openai/o4-mini",
                  "x-ai/grok-3-mini-beta",
                  "openai/chatgpt-4o-latest",
                  "google/gemini-2.5-flash-preview",
                  "google/gemini-2.5-flash-preview:thinking",
                  "google/gemini-2.5-pro-preview",
                       ("google/gemini-2.5-pro-preview-06-05", {"base_model": "google/gemini-2.5-pro-preview"}),
                       "google/gemini-2.0-flash-lite-001",
                  "google/gemini-2.0-flash-001",
                    "google/gemma-3n-e4b-it:free",
                    "google/gemini-2.5-flash-preview-05-20",
                    "google/gemini-2.5-flash-preview-05-20:thinking",
                  "anthropic/claude-3.7-sonnet:thinking",
                  "openai/o3-mini-high",
                  "openai/o3-mini",
                  "mistralai/ministral-3b",
                  "mistral/ministral-8b",
                  "mistralai/mistral-small-3.1-24b-instruct",
                  "mistralai/mistral-medium-3",
                  "meta-llama/llama-4-scout",
                  "meta-llama/llama-4-maverick",
                  "meta-llama/llama-3.3-70b-instruct",
                  "microsoft/phi-4",
                  "openai/o1", "openai/o1-pro", "openai/o3",
                  "deepseek/deepseek-r1", "deepseek/deepseek-r1-0528",
                       "deepseek/deepseek-r1-0528-qwen3-8b",
                       "deepseek/deepseek-chat-v3-0324",
                       "microsoft/phi-4-reasoning-plus",
                       "google/gemma-3-4b-it", "google/gemma-3-12b-it", "google/gemma-3-27b-it",
                  ("qwen/qwen3-30b-a3b-nothink", {"base_model": "qwen/qwen3-30b-a3b", "add_prompt": " /no_think"}),
                  ("qwen/qwen3-30b-a3b-think", {"base_model": "qwen/qwen3-30b-a3b", "add_prompt": " /think"}),
                  ("qwen/qwen3-32b-nothink", {"base_model": "qwen/qwen3-32b", "add_prompt": " /no_think"}),
                  ("qwen/qwen3-32b-think", {"base_model": "qwen/qwen3-32b", "add_prompt": " /think"}),
                  ("qwen/qwen3-235b-a22b-nothink", {"base_model": "qwen/qwen3-235b-a22b", "add_prompt": " /no_think"}),
                  ]

    SELECTED_FOR_SELF_EVALUATION = ["mistralai/ministral-3b",
                                    "mistral/ministral-8b",
                                    "gpt-4.1-nano",
                                    "qwen/qwen3-30b-a3b-nothink",
                                    "qwen/qwen3-14b-nothink",
                                    "mistralai/mistral-small-3.1-24b-instruct",
                                    "meta-llama/llama-4-scout",
                                    "google/gemini-2.0-flash-lite-001",
                                    "google/gemini-2.0-flash-001",
                                    "google/gemini-2.5-flash-preview"]


def get_response(prompt, model_name, parameters=None):
    if parameters is None:
        parameters = {}

    complete_url = Shared.API_URL + "chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Shared.API_KEY}"
    }

    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": model_name,
        "messages": messages,
    }

    enable_streaming = False

    if enable_streaming:
        payload["stream"] = True
        response_message = ""
        thinking_content = ""

        chunk_count = 0

        with requests.post(complete_url, headers=headers, json=payload, stream=True, timeout=20*60) as resp:
            if not resp.status_code == 200:
                print(resp.status_code)

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8")

                # OpenAI-style streaming lines begin with "data: "
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[len("data: "):].strip()
                    if data_str == "[DONE]":
                        # End of stream
                        break
                    try:
                        data_json = json.loads(data_str)
                        if "choices" in data_json:
                            # Each chunk has a delta with partial content
                            chunk_content = data_json["choices"][0]["delta"].get("content", "")
                            chunk_reasoning_content = data_json["choices"][0]["delta"].get("reasoning_content", "")

                            if chunk_content:
                                response_message += chunk_content
                                chunk_count += 1
                                # print(chunk_count)
                                if chunk_count % 10 == 0:
                                    # print(chunk_count, len(response_message), response_message.replace("\n", " ").replace("\r", "").strip())
                                    pass
                            elif chunk_reasoning_content:
                                thinking_content += chunk_reasoning_content
                                chunk_count += 1
                                # print("thinking", chunk_count)
                                if chunk_count % 10 == 0:
                                    # print("thinking", chunk_count, len(response_message), response_message.replace("\n", " ").replace("\r", "").strip())
                                    pass
                    except json.JSONDecodeError:
                        # Possibly a keep-alive or incomplete chunk
                        traceback.print_exc()

        if thinking_content:
            response_message = ["<think>", thinking_content, "</think>", response_message]
            response_message = "\n".join(response_message)
    else:
        with requests.post(complete_url, headers=headers, json=payload, timeout=20*60) as resp:
            if not resp.status_code == 200:
                print(resp.status_code)
                print(resp.text)

            resp_json = resp.json()

            if "choices" not in resp_json:
                print(resp_json)

            message = resp_json["choices"][-1]["message"]

            response_message = message["content"]
            if "reasoning_content" in message:
                response_message = "<think>\n" + message[
                    "reasoning_content"] + "\n</think>\n\n" + response_message.strip()

    return response_message


if __name__ == "__main__":
    print(get_response("How many R are in Strawberry?", "openai/gpt-4.1-mini"))
