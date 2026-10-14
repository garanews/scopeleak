"""Thin client for any OpenAI-compatible server (Ollama, LM Studio, vLLM...)."""
import json
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    local = ROOT / "config.local.json"
    if local.exists():
        config.update(json.loads(local.read_text(encoding="utf-8")))
    return config


def client(config: dict) -> OpenAI:
    # CPU inference with a larger model can take minutes per message.
    return OpenAI(base_url=config["base_url"], api_key=config.get("api_key") or "local",
                  timeout=config.get("timeout", 900))


def list_models(config: dict) -> list[str]:
    return sorted(m.id for m in client(config).models.list().data)


def chat_json(config: dict, messages: list[dict], schema: dict) -> dict:
    response = client(config).chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=config.get("temperature", 0),
        seed=config.get("seed"),
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "result", "schema": schema},
        },
    )
    return json.loads(response.choices[0].message.content)
