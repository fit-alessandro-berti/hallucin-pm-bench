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
                       "qwen/qwen3-235b-a22b-2507",
                       "moonshotai/kimi-k2",
                       "qwen/qwen3-235b-a22b-thinking-2507",
                       "qwen/qwen3-coder",
                       "x-ai/grok-4",
                       "z-ai/glm-4.5",
                       "z-ai/glm-4.5-air",
                       "qwen/qwen3-30b-a3b-instruct-2507",
                       "openrouter/horizon-alpha",
                       "openrouter/horizon-beta",
                       "anthropic/claude-opus-4.1",
                       "openai/gpt-oss-20b",
                       "openai/gpt-oss-120b",
                       "openai/gpt-5-nano",
                       "openai/gpt-5-mini",
                       "openai/gpt-5",
                       "openai/gpt-5-chat",
                       "qwen/qwen3-30b-a3b-thinking-2507",
                       ("deepcogito/cogito-v2-preview-llama-109b-moe", {"base_model": "deepcogito/cogito-v2-preview-llama-109b-moe", "payload": {"reasoning": {"enabled": True}}}),
                       ("deepcogito/cogito-v2-preview-deepseek-671b", {"base_model": "deepcogito/cogito-v2-preview-deepseek-671b", "payload": {"reasoning": {"enabled": True}}}),
                       "moonshotai/kimi-k2-0905",
                       "qwen/qwen3-max",
                       "openrouter/sonoma-dusk-alpha",
                       "openrouter/sonoma-sky-alpha",
                       "qwen/qwen3-next-80b-a3b-instruct",
                       "qwen/qwen3-next-80b-a3b-thinking",
                       "nvidia/nemotron-nano-9b-v2",
                       ("gpt-5-high", {"base_model": "openai/gpt-5", "payload": {"reasoning_effort": "high"}}),
                       ("openai/gpt-oss-120b-high", {"base_model": "openai/gpt-oss-120b", "payload": {"reasoning_effort": "high"}}),
                       ("openai/o3-pro-high", {"base_model": "openai/o3-pro", "payload": {"reasoning_effort": "high"}}),
                       "google/gemini-2.5-pro",
                       "ai21/jamba-mini-1.7",
                       "ai21/jamba-large-1.7",
                       "mistralai/mistral-medium-3.1",
                       "baidu/ernie-4.5-21b-a3b",
                       "deepseek/deepseek-chat-v3.1",
                       "x-ai/grok-code-fast-1",
                       "nousresearch/hermes-4-70b",
                       "nousresearch/hermes-4-405b",
                  "google/gemini-2.5-flash",
                  "google/gemini-2.5-flash-lite-preview-06-17",
                  "google/gemini-2.0-flash-lite-001",
                  "google/gemini-2.0-flash-001",
                    "google/gemma-3n-e4b-it:free",
                  "anthropic/claude-3.7-sonnet:thinking",
                  "openai/o3-mini-high",
                  "openai/o3-mini",
                       "openrouter/cypher-alpha:free",
                  "mistralai/ministral-3b",
                  "mistral/ministral-8b",
                  "mistralai/mistral-small-3.1-24b-instruct",
                  "mistralai/mistral-medium-3",
                  "meta-llama/llama-4-scout",
                  "meta-llama/llama-4-maverick",
                  "meta-llama/llama-3.3-70b-instruct",
                       "inception/mercury",
                       "baidu/ernie-4.5-300b-a47b",
                  "microsoft/phi-4",
                  "openai/o1", "openai/o1-pro", "openai/o3", "openai/o3-pro",
                       "mistralai/magistral-medium-2506",
                       "mistralai/magistral-medium-2506:thinking",
                       "mistralai/magistral-small-2506",
                       "mistralai/mistral-small-3.2-24b-instruct",
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

    if "payload" in parameters:
        payload.update(parameters["payload"])

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
