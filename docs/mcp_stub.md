# Local MCP Stub — `dummy_mcp/`

## What it is

`dummy_mcp/` is a **minimal local Python package** that satisfies the
`mcp` dependency in CrewAI's package resolver without pulling in the full
MCP SDK or enabling any real MCP infrastructure.

It is wired in [`pyproject.toml`](../pyproject.toml) via:

```toml
[tool.uv.sources]
mcp = { path = "./dummy_mcp" }
```

This means `import mcp` resolves to the stub, not to the published
[`mcp`](https://pypi.org/project/mcp/) package on PyPI.

---

## Why it exists

CrewAI `1.14.7` lists `mcp` as a dependency. In the Hoch Agent Swarm
workflow, no MCP tools, transports, or servers are used — the crew runs
entirely against an Ollama local inference backend. Installing the full
MCP SDK would bring in unnecessary network dependencies and event-loop
requirements that conflict with the bounded local execution model.

The stub satisfies the import check at runtime while keeping the
dependency tree clean and fully offline-capable.

---

## Boundaries — what the stub does NOT provide

> [!CAUTION]
> Do not enable any of the following while the stub is active.
> They will silently fail or produce undefined behaviour.

- MCP tool calls
- MCP resource reads or writes
- MCP prompt templates
- MCP server transports (stdio, SSE, HTTP)
- MCP session management
- MCP sampling or completion requests

---

## Verifying the stub is active

```bash
uv run python -c "
import crewai, mcp
print('crewai ok', crewai.__version__)
print('mcp stub ok', getattr(mcp, '__version__', 'no version'))
"
```

Expected output:

```
crewai ok 1.14.7
mcp stub ok 1.26.0
```

The version string (`1.26.0`) is the stub's declared version, not the
real MCP SDK version. If you see a different version, the real package
may have been installed.

---

## Restoring the real `mcp` package

When real MCP integration is needed:

1. Remove the `[tool.uv.sources]` override from `pyproject.toml`:

   ```toml
   # Remove or comment out:
   # [tool.uv.sources]
   # mcp = { path = "./dummy_mcp" }
   ```

2. Sync dependencies:

   ```bash
   uv sync
   ```

3. Verify the real package is installed:

   ```bash
   uv run python -c "import mcp; print(mcp.__version__)"
   ```

4. Implement actual MCP tools in `src/hoch_agent_swarm/tools/` and
   attach them to agents in `crew.py`.

---

## Scope boundary

This stub is intentionally sealed. Do **not** modify `dummy_mcp/` to
add real MCP functionality — create a proper migration batch instead,
replacing the stub cleanly and updating all affected tests.
