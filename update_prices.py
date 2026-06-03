import json
import httpx
from datetime import datetime, timezone

JSON_PATH = "pricing.json"
LITELLM_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


def fetch_latest_rates():
    print("▶ Fetching latest model rates from LiteLLM...")

    response = httpx.get(LITELLM_URL, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch rates, HTTP {response.status_code}")

    litellm_data = response.json()

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        local_config = json.load(f)

    # Left: LiteLLM key  →  Right: pricing.json key
    # Only include models confirmed to exist in LiteLLM with accurate direct-API pricing.
    # Qwen / GLM / deepseek-v2.5 are absent from LiteLLM; they retain hardcoded values.
    name_map = {
        # OpenAI
        "gpt-4o":            "gpt-4o",
        "gpt-4o-mini":       "gpt-4o-mini",
        "gpt-5":             "gpt-5",
        "gpt-5.4-mini":      "gpt-5.4-mini",
        "o3":                "o3",
        "o4-mini":           "o4-mini",
        # Anthropic — use versioned keys to avoid aliasing different tier models
        "claude-opus-4-1":   "claude-opus-4",
        "claude-sonnet-4-6": "claude-sonnet-4",
        "claude-haiku-4-5":  "claude-haiku-4",
        # Google
        "gemini-2.0-flash":  "gemini-2.0-flash",
        "gemini-2.5-pro":    "gemini-2.5-pro",
        # DeepSeek
        "deepseek-chat":     "deepseek-v3",
        "deepseek-reasoner": "deepseek-r1",
    }

    models = local_config.get("models", {})
    updated_count = 0

    for litellm_id, local_key in name_map.items():
        if litellm_id not in litellm_data:
            print(f"  [SKIP] {litellm_id} not found in LiteLLM")
            continue
        if local_key not in models:
            print(f"  [SKIP] {local_key} not found in pricing.json")
            continue

        item = litellm_data[litellm_id]
        inp = float(item.get("input_cost_per_token", 0)) * 1_000_000
        out = float(item.get("output_cost_per_token", 0)) * 1_000_000

        old_inp = models[local_key].get("input", 0)
        old_out = models[local_key].get("output", 0)

        models[local_key]["input"]  = round(inp, 4)
        models[local_key]["output"] = round(out, 4)

        changed = old_inp != round(inp, 4) or old_out != round(out, 4)
        tag = "[CHANGED]" if changed else "[SAME]"
        print(f"  {tag} {local_key}: {inp:.4f}/{out:.4f} per 1M tokens")
        updated_count += 1

    if updated_count > 0:
        local_config["updated_at"] = datetime.now(timezone.utc).date().isoformat()
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(local_config, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Done — {updated_count} models synced, pricing.json written.")
    else:
        print("\n➔ No models updated (all LiteLLM keys missing). pricing.json unchanged.")


if __name__ == "__main__":
    fetch_latest_rates()
