"""Founder-facing Grok Voice Agent tool pack (export for paste / binding)."""

from __future__ import annotations

from typing import Any, Dict, List

from backend.voice.tools_schema import grok_voice_tools


def build_grok_tool_pack(*, base_url: str = "https://YOUR-HELM-ORIGIN") -> Dict[str, Any]:
    """Structured pack: persona pointer + tools with full HTTP binding examples."""
    tools = grok_voice_tools()
    # Ensure revenue + security event tools are present (added in tools_schema)
    base = base_url.rstrip("/")
    http_tools: List[Dict[str, Any]] = []
    for t in tools:
        fn = t.get("function") or {}
        xh = fn.get("x_helm_http") or {}
        path = xh.get("path") or ""
        method = xh.get("method") or "GET"
        url = base + path if path.startswith("/") else f"{base}/{path}"
        http_tools.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description"),
                "method": method,
                "url_template": url,
                "parameters": fn.get("parameters"),
            }
        )

    return {
        "schema": "helm-grok-voice-tool-pack-v2",
        "title": "HELM Executive Mission Commander — Grok Voice Tool Pack",
        "base_url": base,
        "persona_prompt_path": "docs/prompts/helm_voice_executive_commander.md",
        "doctrine": [
            "Call tools for every LIVE metric",
            "Tool fail or UNKNOWN → say UNKNOWN; never invent dashboards",
            "DOORSTEP (deploy/spend/keys/sign/money) is never auto-executed",
            "Revenue dollars only from verified SETTLED ledger via helm_revenue",
            "Security speech is HIGH-only and rate-limited",
        ],
        "setup_steps": [
            "1. Create a Grok Voice Agent in Grok Voice Agents (Beta).",
            "2. Paste the persona from docs/prompts/helm_voice_executive_commander.md into use-case.",
            f"3. Set HELM base URL to your LIVE origin (replace {base} if placeholder).",
            "4. Register each tool below as an HTTP / function tool mapped to the URL template.",
            "5. Or poll GET {base}/api/v1/helm/voice/tools for live schemas.",
            "6. Enable local TTS only on the HELM /voice desk if you want browser speech; Grok has its own TTS.",
        ],
        "tools": http_tools,
        "quick_smoke": [
            f"GET {base}/api/v1/helm/voice/health",
            f"GET {base}/api/v1/helm/voice/brief",
            f"GET {base}/api/v1/helm/voice/revenue",
            f"GET {base}/api/v1/helm/voice/security/events",
            f"GET {base}/api/v1/helm/voice/factory/HASF",
            f"GET {base}/api/v1/helm/voice/role/ciso",
        ],
        "openapi_style_tools": tools,
    }


def render_grok_pack_markdown(pack: Dict[str, Any]) -> str:
    lines = [
        f"# {pack['title']}",
        "",
        f"**Base URL:** `{pack['base_url']}`",
        "",
        "## Setup",
        "",
    ]
    for s in pack.get("setup_steps") or []:
        lines.append(f"- {s}")
    lines.extend(["", "## Doctrine", ""])
    for d in pack.get("doctrine") or []:
        lines.append(f"- {d}")
    lines.extend(["", "## Tools", ""])
    for t in pack.get("tools") or []:
        lines.append(f"### `{t.get('name')}`")
        lines.append("")
        lines.append(f"- **Method:** `{t.get('method')}`")
        lines.append(f"- **URL:** `{t.get('url_template')}`")
        lines.append(f"- **Description:** {t.get('description')}")
        lines.append("")
    lines.extend(["## Smoke checks", ""])
    for q in pack.get("quick_smoke") or []:
        lines.append(f"- `{q}`")
    lines.append("")
    lines.append(
        "Persona source: `docs/prompts/helm_voice_executive_commander.md` — "
        "copy that file into the Grok agent use-case field."
    )
    lines.append("")
    return "\n".join(lines)
