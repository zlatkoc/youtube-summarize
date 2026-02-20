# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server that retrieves YouTube video transcripts and optionally summarizes them. It uses the `youtube_transcript_api` Python library directly and exposes its functionality as MCP tools.

## Key Commands

```bash
# Install dependencies
uv sync

# Run the MCP server (stdio transport)
uv run mcp run main.py

# Run the MCP dev inspector (web UI for testing)
uv run mcp dev main.py
```

## Architecture

- **Entry point**: `main.py` — defines the FastMCP server instance and all MCP tools
- **Transport**: stdio-based MCP server (launched via `mcp run`)
- **Library**: `youtube_transcript_api` — used directly as a Python library (not as a subprocess/CLI)

### MCP Tools

1. **`get_transcript`** — fetch a YouTube video's transcript in a specified format (json, pretty, text, webvtt, srt), with optional language selection
2. **`list_transcripts`** — list available transcript languages for a video
3. **`summarize_transcript`** — fetch transcript and return it with summarization instructions for the LLM client to act on

### Design Decisions

- Uses `youtube_transcript_api` as a Python library directly (structured data, proper exceptions, no subprocess overhead)
- Formatter classes from `youtube_transcript_api.formatters` handle output formatting (JSON, Text, SRT, WebVTT, PrettyPrint)
- The summarization tool returns the transcript with a prompt/instruction for the LLM to summarize, rather than calling an external LLM API itself (the MCP client/LLM handles summarization)
- Video IDs are extracted from full YouTube URLs when provided (supports `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`, `youtube.com/shorts/`, and bare 11-char IDs)
- Tools return error strings rather than raising exceptions — the LLM client can act on them

## Dependencies

- `mcp[cli]` — MCP SDK with CLI support (provides `FastMCP` and `mcp run`/`mcp dev` commands)
- `youtube-transcript-api` — Python library for fetching YouTube transcripts (provides API client and formatters)

## Releasing

Releases are triggered by creating a GitHub Release (not just a tag). The workflow (`.github/workflows/publish.yml`) runs three jobs:

1. **pypi** — builds and publishes the package to PyPI (version derived from the git tag via `SETUPTOOLS_SCM_PRETEND_VERSION`)
2. **update-server-json** — updates `server.json` with the new version and commits it to `main`
3. **mcp-registry** — publishes to the MCP Registry (runs after pypi and update-server-json)

To release:

```bash
git tag v0.X.Y
git push origin v0.X.Y
gh release create v0.X.Y --title "v0.X.Y" --notes "Release notes here"
```

## Python Version

Python 3.13+ (managed via `.python-version` and uv)
