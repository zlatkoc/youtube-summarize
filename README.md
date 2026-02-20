# youtube-summarize

MCP server that fetches YouTube video transcripts and optionally summarizes them.

## Features

- **Fetch transcripts** in multiple formats (text, JSON, SRT, WebVTT, pretty-print)
- **Summarize videos** — returns transcript with instructions for the LLM to produce a summary
- **List available languages** for any video's transcripts
- **Flexible URL parsing** — accepts full YouTube URLs (`youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`, `youtube.com/shorts/`) or bare video IDs
- **Multi-language support** — request transcripts in specific languages with fallback priority

## Tools

### `get_transcript`

Fetch a YouTube video's transcript.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | *required* | YouTube video URL or video ID |
| `languages` | string[] | `["en"]` | Preferred languages in priority order |
| `format` | string | `"text"` | Output format: `text`, `json`, `pretty`, `webvtt`, `srt` |
| `preserve_formatting` | boolean | `false` | Keep HTML formatting tags in the transcript |

### `summarize_transcript`

Fetch a transcript and return it with summarization instructions for the LLM client.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | *required* | YouTube video URL or video ID |
| `prompt` | string | *(default prompt)* | Custom summarization instructions |
| `languages` | string[] | `["en"]` | Preferred languages in priority order |

### `list_transcripts`

List available transcript languages for a video.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | *required* | YouTube video URL or video ID |

## Installation

### Quick start (recommended)

```bash
uvx youtube-summarize
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "youtube-summarize": {
      "command": "uvx",
      "args": ["youtube-summarize"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add youtube-summarize -- uvx youtube-summarize
```

### Other MCP clients

Run the server over stdio:

```bash
uvx youtube-summarize
```

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

## Development

```bash
# Install dependencies
uv sync

# Launch the MCP inspector (web UI for testing tools)
uv run mcp dev main.py
```

## License

MIT
