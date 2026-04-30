import os

import requests
import traceback
import json


REQUEST_CONTEXT_PARAM = "request_context"
REQUEST_CONTEXT_ANSWER = "answer"
REQUEST_CONTEXT_EVALUATION = "evaluation"
REQUEST_CONTEXT_UNKNOWN = "unknown"
API_KEY_ENV_PARAM = "api_key_env"

EVALUATIONS_DIR = "evaluations-dsv4pro"


def _uses_responses_api(api_url):
    return "api.x.ai" in api_url


def _build_api_url(api_url, endpoint):
    return api_url.rstrip("/") + "/" + endpoint.lstrip("/")


def _build_payload(prompt, model_name, parameters, use_responses_api):
    payload = dict(parameters.get("payload", {}))

    if use_responses_api and "reasoning_effort" in payload and "reasoning" not in payload:
        payload["reasoning"] = {"effort": payload.pop("reasoning_effort")}

    if use_responses_api:
        payload.update({
            "model": model_name,
            "input": prompt,
        })
    else:
        payload.update({
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
        })

    return payload


def _extract_responses_reasoning(resp_json):
    reasoning_parts = []

    for item in resp_json.get("output", []):
        if item.get("type") != "reasoning":
            continue

        for summary_item in item.get("summary", []):
            if isinstance(summary_item, dict) and summary_item.get("text"):
                reasoning_parts.append(summary_item["text"])

    return "\n".join(reasoning_parts).strip()


def _extract_responses_message(resp_json):
    if resp_json.get("output_text"):
        return resp_json["output_text"]

    message_parts = []

    for item in resp_json.get("output", []):
        if item.get("type") != "message":
            continue

        for content_item in item.get("content", []):
            if not isinstance(content_item, dict):
                continue

            if content_item.get("type") in {"output_text", "text"} and content_item.get("text"):
                message_parts.append(content_item["text"])

    return "\n".join(message_parts).strip()


def _extract_text_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (_extract_text_value(item) for item in value))).strip()
    if isinstance(value, dict):
        parts = []
        for key in ("text", "content", "output_text", "reasoning", "thinking", "reasoning_content"):
            text = _extract_text_value(value.get(key))
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    return str(value)


def _extract_chat_message_parts(message):
    content = message.get("content", "")
    if isinstance(content, str):
        return content, _extract_text_value(message.get("reasoning_content"))

    if not isinstance(content, list):
        return _extract_text_value(content), _extract_text_value(message.get("reasoning_content"))

    message_parts = []
    reasoning_parts = []

    for item in content:
        if isinstance(item, dict):
            item_type = item.get("type", "")
            is_reasoning = item_type in {"reasoning", "thinking", "reasoning_content"}

            for key in ("text", "content", "output_text"):
                text = _extract_text_value(item.get(key))
                if text:
                    if is_reasoning:
                        reasoning_parts.append(text)
                    else:
                        message_parts.append(text)

            for key in ("reasoning", "thinking", "reasoning_content"):
                text = _extract_text_value(item.get(key))
                if text:
                    reasoning_parts.append(text)
        else:
            text = _extract_text_value(item)
            if text:
                message_parts.append(text)

    top_level_reasoning = _extract_text_value(message.get("reasoning_content"))
    if top_level_reasoning:
        reasoning_parts.append(top_level_reasoning)

    return "\n".join(message_parts).strip(), "\n".join(reasoning_parts).strip()


def _final_response_only(response_message, reasoning_content):
    return response_message


def _parse_response_json(resp_json, use_responses_api):
    if use_responses_api:
        response_message = _extract_responses_message(resp_json)
        reasoning_content = _extract_responses_reasoning(resp_json)

        return _final_response_only(response_message, reasoning_content)

    if "choices" not in resp_json:
        print(resp_json)

    message = resp_json["choices"][-1]["message"]

    response_message, reasoning_content = _extract_chat_message_parts(message)
    return _final_response_only(response_message, reasoning_content)



class Shared:
    MODEL_CATALOGUE = ["openai/gpt-4.1",
                  "openai/gpt-4.1-mini",
                  "openai/gpt-4.5-preview",
                  "anthropic/claude-3.7-sonnet",
                  "anthropic/claude-sonnet-4", "anthropic/claude-opus-4",
                  "x-ai/grok-3-beta",
                  "openai/o4-mini-high",
                  "openai/o4-mini",
                       "x-ai/grok-4",
                       "anthropic/claude-opus-4.1",
                       "openai/gpt-oss-20b",
                       "openai/gpt-oss-120b",
                       "openai/gpt-3.5-turbo",
                       "openai/gpt-4-turbo",
                       "mistralai/mixtral-8x22b-instruct",
                       "qwen/qwen3-max",
                       ("openai/gpt-oss-120b-high", {"base_model": "openai/gpt-oss-120b", "payload": {"reasoning_effort": "high"}}),
                       "google/gemini-2.5-pro",
                       "mistralai/mistral-medium-3.1",
                       ("deepseek/deepseek-v3.2-speciale",
                        {"base_model": "deepseek/deepseek-v3.2-speciale",
                         "payload": {"reasoning": {"enabled": True}}}),
                       ("deepseek/deepseek-v3.2",
                        {"base_model": "deepseek/deepseek-v3.2",
                         "payload": {"reasoning": {"enabled": True}}}),
                       ("nvidia/nemotron-3-nano-30b-a3b-thinking",
                        {"base_model": "nvidia/nemotron-3-nano-30b-a3b:free",
                         "payload": {"reasoning": {"enabled": True}}}),
                       ("openai/gpt-5.2-codex-xhigh",
                        {"base_model": "openai/gpt-5.2-codex",
                         "payload": {"reasoning": {"effort": "xhigh"}}}),
                       ("openai/gpt-5.3-codex-xhigh",
                        {"base_model": "openai/gpt-5.3-codex",
                         "payload": {"reasoning": {"effort": "xhigh"}}}),
                       "qwen/qwen3.5-35b-a3b",
                       "qwen/qwen3.5-27b",
                       "qwen/qwen3.5-122b-a10b",
                       "anthropic/claude-sonnet-4.5",
                       "baidu/ernie-4.5-21b-a3b-thinking",
                       "anthropic/claude-haiku-4.5",
                       "moonshotai/kimi-k2-thinking",
                       "mistralai/mistral-large-2512",
                       "amazon/nova-2-lite-v1",
                       "moonshotai/kimi-k2.5",
                       "z-ai/glm-5",
                       "qwen/qwen3.5-397b-a17b",
                       "google/gemini-3.1-pro-preview",
                       "inception/mercury-2",
                       "qwen/qwen3.5-9b",
                       "bytedance-seed/seed-2.0-lite",
                       "bytedance-seed/seed-2.0-mini",
                       "minimax/minimax-m2.7",
                       "arcee-ai/trinity-large-thinking",
                       "z-ai/glm-5v-turbo",
                       "qwen/qwen3.6-plus:free",
                       "google/gemma-4-26b-a4b-it",
                       "google/gemma-4-31b-it",
                       "z-ai/glm-5.1",
                       "Meta-Muse-Spark-20260414",
                       "moonshotai/kimi-k2.6",
                       "ChatGPT-5.5-Pro-20260422",
                       "xiaomi/mimo-v2.5-pro",
                       "xiaomi/mimo-v2.5",
                       "inclusionai/ling-2.6-1t:free",
                       "tencent/hy3-preview:free",
                       "deepseek/deepseek-v4-flash",
                       "deepseek/deepseek-v4-pro",
                       "qwen/qwen3.6-max-preview", "qwen/qwen3.6-27b", "qwen/qwen3.6-flash",
                       "qwen/qwen3.6-35b-a3b",
                       "poolside/laguna-m.1:free", "poolside/laguna-xs.2:free",
                       ("anthropic/claude-opus-4.7-thinking",
                        {"base_model": "anthropic/claude-opus-4.7",
                         "payload": {"reasoning": {"enabled": True}}}),
                       ("anthropic/claude-opus-4.6-thinking",
                        {"base_model": "anthropic/claude-opus-4.6",
                         "payload": {"reasoning": {"enabled": True}}}),
                       ("anthropic/claude-sonnet-4.6-thinking",
                        {"base_model": "anthropic/claude-sonnet-4.6",
                         "payload": {"reasoning": {"enabled": True}}}),
                       ("mistral-medium-3.5",
                        {"base_model": "mistral-medium-3.5", "api_url": "https://api.mistral.ai/v1/",
                         "api_key_env": "MISTRAL_API_KEY"}),
                       ("mistral-medium-3.5-thinkhigh",
                        {"base_model": "mistral-medium-3.5", "api_url": "https://api.mistral.ai/v1/",
                         "api_key_env": "MISTRAL_API_KEY", "payload": {"reasoning_effort": "high"}}),
                       ("gpt-5.2-2025-12-11-none",
                        {"base_model": "gpt-5.2-2025-12-11", "api_url": "https://api.openai.com/v1/", "api_key_env": "OPENAI_API_KEY"}),
                       ("gpt-5.2-2025-12-11-high",
                        {"base_model": "gpt-5.2-2025-12-11", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "high"}}),
                       ("gpt-5.2-2025-12-11-medium",
                        {"base_model": "gpt-5.2-2025-12-11", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "medium"}}),
                       ("gpt-5.2-2025-12-11-xhigh",
                        {"base_model": "gpt-5.2-2025-12-11", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "xhigh"}}),
                       ("gpt-5.4-2026-03-05-none",
                        {"base_model": "gpt-5.4-2026-03-05", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY"}),
                       ("gpt-5.4-2026-03-05-high",
                        {"base_model": "gpt-5.4-2026-03-05", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "high"}}),
                       ("gpt-5.4-2026-03-05-medium",
                        {"base_model": "gpt-5.4-2026-03-05", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "medium"}}),
                       ("gpt-5.4-2026-03-05-xhigh",
                        {"base_model": "gpt-5.4-2026-03-05", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "xhigh"}}),
                       ("gpt-5.5-2026-04-23-none",
                        {"base_model": "gpt-5.5-2026-04-23", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY"}),
                       ("gpt-5.5-2026-04-23-high",
                        {"base_model": "gpt-5.5-2026-04-23", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "high"}}),
                       ("gpt-5.5-2026-04-23-medium",
                        {"base_model": "gpt-5.5-2026-04-23", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "medium"}}),
                       ("gpt-5.5-2026-04-23-xhigh",
                        {"base_model": "gpt-5.5-2026-04-23", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "xhigh"}}),
                       ("gpt-5.4-mini-2026-03-17-high",
                        {"base_model": "gpt-5.4-mini-2026-03-17", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "high"}}),
                       ("gpt-5.4-mini-2026-03-17-none",
                        {"base_model": "gpt-5.4-mini-2026-03-17", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "none"}}),
                       ("gpt-5.4-nano-2026-03-17-high",
                        {"base_model": "gpt-5.4-nano-2026-03-17", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "high"}}),
                       ("gpt-5.4-nano-2026-03-17-none",
                        {"base_model": "gpt-5.4-nano-2026-03-17", "api_url": "https://api.openai.com/v1/",
                         "api_key_env": "OPENAI_API_KEY", "payload": {"reasoning_effort": "none"}}),
                       ("grok-4.20-experimental-beta-0304-non-reasoning",
                        {"base_model": "grok-4.20-experimental-beta-0304-non-reasoning", "api_url": "https://api.x.ai/v1/",
                         "api_key_env": "GROK_API_KEY"}),
                       ("grok-4.20-experimental-beta-0304-reasoning",
                        {"base_model": "grok-4.20-experimental-beta-0304-reasoning",
                         "api_url": "https://api.x.ai/v1/",
                         "api_key_env": "GROK_API_KEY"}),
                       ("grok-4.20-multi-agent-experimental-beta-0304",
                        {"base_model": "grok-4.20-multi-agent-experimental-beta-0304",
                         "api_url": "https://api.x.ai/v1/",
                         "api_key_env": "GROK_API_KEY"}),
                       ("grok-4.20-heavy",
                        {"base_model": "grok-4.20-multi-agent-experimental-beta-0304",
                         "api_url": "https://api.x.ai/v1/",
                         "api_key_env": "GROK_API_KEY",
                         "payload": {"reasoning": {"effort": "high"}}}),
                       ("nvidia/NVIDIA-Nemotron-3-Super-120B-A12B",
                        {"base_model": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B",
                         "api_key_env": "DEEPINFRA_API_KEY",
                         "api_url": "https://api.deepinfra.com/v1/openai/"}),
                       "Grok-4.1-20251118",
                       "google/gemini-2.5-flash",
                       "z-ai/glm-5-turbo",
                  "anthropic/claude-3.7-sonnet:thinking",
                  "meta-llama/llama-4-maverick",
                       "baidu/ernie-4.5-300b-a47b",
                  "microsoft/phi-4",
                  "openai/o1", "openai/o1-pro", "openai/o3",
                       ("x-ai/grok-4.1-fast",
                        {"base_model": "x-ai/grok-4.1-fast",
                         "payload": {"reasoning": {"enabled": False}}}),
                       ("x-ai/grok-4.1-fast-thinking",
                        {"base_model": "x-ai/grok-4.1-fast",
                         "payload": {"reasoning": {"enabled": True}}}),
                       "allenai/olmo-3-32b-think",
                       "anthropic/claude-opus-4.5",
                       "prime-intellect/intellect-3",
                       ("google/gemini-3-flash-preview",
                        {"base_model": "google/gemini-3-flash-preview",
                         "payload": {"reasoning": {"enabled": False}}}),
                       ("google/gemini-3-flash-preview-thinking",
                        {"base_model": "google/gemini-3-flash-preview",
                         "payload": {"reasoning": {"enabled": True}}}),
                       ("google/gemini-3.1-flash-lite-preview",
                        {"base_model": "google/gemini-3.1-flash-lite-preview",
                         "payload": {"reasoning": {"enabled": False}}}),
                       ("google/gemini-3.1-flash-lite-preview-thinking",
                        {"base_model": "google/gemini-3.1-flash-lite-preview",
                         "payload": {"reasoning": {"enabled": True}}}),
                       "openai/gpt-5.3-chat",
                  ]

    SELECTED_FOR_SELF_EVALUATION = ["mistralai/ministral-3b",
                                    "mistral/ministral-8b",
                                    "gpt-4.1-nano",
                                    "qwen/qwen3-30b-a3b-nothink",
                                    "qwen/qwen3-14b-nothink",
                                    "meta-llama/llama-4-scout",
                                    "google/gemini-2.0-flash-lite-001",
                                    "google/gemini-2.0-flash-001",
                                    "google/gemini-2.5-flash-preview"]


def get_response(prompt, model_name, parameters=None):
    if parameters is None:
        parameters = {}

    request_context = parameters.get(REQUEST_CONTEXT_PARAM, REQUEST_CONTEXT_UNKNOWN)
    api_url = parameters["api_url"] if "api_url" in parameters else "https://openrouter.ai/api/v1/"
    if "api_key" in parameters:
        api_key = parameters["api_key"]
    elif API_KEY_ENV_PARAM in parameters:
        api_key = os.environ[parameters[API_KEY_ENV_PARAM]]
    else:
        api_key = os.environ["OPENROUTER_API_KEY"]
    use_responses_api = _uses_responses_api(api_url)

    complete_url = _build_api_url(api_url, "responses" if use_responses_api else "chat/completions")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = _build_payload(prompt, model_name, parameters, use_responses_api)

    enable_streaming = False

    if enable_streaming:
        payload["stream"] = True
        response_message = ""
        thinking_content = ""

        chunk_count = 0

        with requests.post(complete_url, headers=headers, json=payload, stream=True, timeout=20*60) as resp:
            if not resp.status_code == 200:
                print(request_context, resp.status_code)

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
                        if use_responses_api:
                            if data_json.get("type") == "response.output_text.delta":
                                chunk_content = data_json.get("delta", "")
                                if chunk_content:
                                    response_message += chunk_content
                                    chunk_count += 1
                            elif data_json.get("type") == "response.reasoning_summary_text.delta":
                                chunk_reasoning_content = data_json.get("delta", "")
                                if chunk_reasoning_content:
                                    thinking_content += chunk_reasoning_content
                                    chunk_count += 1
                        elif "choices" in data_json:
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

    else:
        with requests.post(complete_url, headers=headers, json=payload, timeout=20*60) as resp:
            if not resp.status_code == 200:
                print(request_context, resp.status_code)
                print(resp.text)

            resp_json = resp.json()
            response_message = _parse_response_json(resp_json, use_responses_api)

    return response_message


if __name__ == "__main__":
    print(get_response("How many R are in Strawberry?", "openai/gpt-4.1-mini"))
