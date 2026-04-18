"""Central Gemini model ids and interview defaults (no I/O)."""

from __future__ import annotations

DEFAULT_FLASH_LITE_MODEL_ID = "gemini-3.1-flash-lite-preview"
DEFAULT_PRO_MODEL_ID = "gemini-3.1-pro-preview"
ROUTER_GENERATE_TEMPERATURE = 0.1

THINKING_SEED_BY_AGENT_ID: dict[int, str] = {
    1: "LOW",
    2: "LOW",
    3: "LOW",
    4: "LOW",
    5: "HIGH",
}
