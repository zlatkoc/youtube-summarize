import re

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import (
    JSONFormatter,
    PrettyPrintFormatter,
    SRTFormatter,
    TextFormatter,
    WebVTTFormatter,
)

mcp = FastMCP("youtube-summary")

api = YouTubeTranscriptApi()

FORMATTERS = {
    "json": JSONFormatter(),
    "pretty": PrettyPrintFormatter(),
    "text": TextFormatter(),
    "webvtt": WebVTTFormatter(),
    "srt": SRTFormatter(),
}

DEFAULT_SUMMARY_PROMPT = (
    "Summarize the following YouTube video transcript. "
    "Provide a concise overview of the main topics, key points, and conclusions."
)

VIDEO_ID_REGEX = re.compile(
    r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)"
    r"([A-Za-z0-9_-]{11})"
)
BARE_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url_or_id: str) -> str:
    """Extract a YouTube video ID from a URL or bare ID string."""
    url_or_id = url_or_id.strip()
    if BARE_ID_REGEX.match(url_or_id):
        return url_or_id
    match = VIDEO_ID_REGEX.search(url_or_id)
    if match:
        return match.group(1)
    raise ValueError(
        f"Could not extract a YouTube video ID from: {url_or_id}"
    )


def _format_transcript(transcript, fmt: str) -> str:
    """Format a FetchedTranscript using the specified formatter."""
    formatter = FORMATTERS.get(fmt)
    if formatter is None:
        return f"Error: Unknown format '{fmt}'. Choose from: {', '.join(FORMATTERS)}"
    return formatter.format_transcript(transcript)


def _handle_transcript_error(e: Exception, video_id: str, languages: list[str] | None = None) -> str:
    """Convert youtube_transcript_api exceptions into user-friendly error strings."""
    from youtube_transcript_api import (
        AgeRestricted,
        InvalidVideoId,
        IpBlocked,
        NoTranscriptFound,
        RequestBlocked,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    if isinstance(e, TranscriptsDisabled):
        return f"Error: Transcripts are disabled for video '{video_id}'."
    if isinstance(e, NoTranscriptFound):
        lang_str = ", ".join(languages) if languages else "any"
        return (
            f"Error: No transcript found for video '{video_id}' "
            f"in language(s): {lang_str}. Use list_transcripts to see available languages."
        )
    if isinstance(e, VideoUnavailable):
        return f"Error: Video '{video_id}' is unavailable."
    if isinstance(e, InvalidVideoId):
        return f"Error: '{video_id}' is not a valid YouTube video ID."
    if isinstance(e, AgeRestricted):
        return f"Error: Video '{video_id}' is age-restricted and cannot be accessed."
    if isinstance(e, IpBlocked):
        return "Error: YouTube is blocking requests from this IP address."
    if isinstance(e, RequestBlocked):
        return "Error: The request to YouTube was blocked."
    return f"Error fetching transcript for '{video_id}': {e}"


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to [HH:MM:SS] string."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def _format_transcript_with_timestamps(transcript) -> str:
    """Render a FetchedTranscript as text with an [HH:MM:SS] prefix on each line."""
    return "\n".join(
        f"{_format_timestamp(snippet.start)} {snippet.text}" for snippet in transcript
    )


class _SilentLogger:
    def debug(self, _msg): pass
    def info(self, _msg): pass
    def warning(self, _msg): pass
    def error(self, _msg): pass


def _fetch_metadata(video_id: str) -> dict | None:
    """Fetch video metadata via yt-dlp. Returns None on any failure."""
    try:
        from yt_dlp import YoutubeDL

        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "logger": _SilentLogger(),
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=False,
            )
        if not info:
            return None
        return {
            "title": info.get("title"),
            "description": info.get("description"),
            "channel": info.get("channel") or info.get("uploader"),
            "channel_id": info.get("channel_id"),
            "channel_url": info.get("channel_url") or info.get("uploader_url"),
            "upload_date": info.get("upload_date"),
            "duration_seconds": info.get("duration"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "tags": info.get("tags") or [],
            "categories": info.get("categories") or [],
            "thumbnail_url": info.get("thumbnail"),
            "chapters": info.get("chapters") or [],
            "age_limit": info.get("age_limit"),
            "is_live": info.get("is_live"),
            "webpage_url": info.get("webpage_url"),
        }
    except Exception:
        return None


def _format_hms(seconds: float | int) -> str:
    """Format seconds as HH:MM:SS (no brackets)."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _format_upload_date(yyyymmdd: str | None) -> str | None:
    if not yyyymmdd or len(yyyymmdd) != 8:
        return yyyymmdd
    return f"{yyyymmdd[0:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def _format_metadata_block(meta: dict | None, header: str = "METADATA") -> str:
    """Render a [METADATA] block, or [METADATA_ERROR] when meta is None."""
    if meta is None:
        return "[METADATA_ERROR]\nFailed to fetch video metadata."
    lines = [f"[{header}]"]
    if meta.get("title"):
        lines.append(f"Title: {meta['title']}")
    if meta.get("channel"):
        lines.append(f"Channel: {meta['channel']}")
    pub = _format_upload_date(meta.get("upload_date"))
    if pub:
        lines.append(f"Published: {pub}")
    if meta.get("duration_seconds") is not None:
        lines.append(f"Duration: {_format_hms(meta['duration_seconds'])}")
    if meta.get("view_count") is not None:
        lines.append(f"Views: {meta['view_count']:,}")
    if meta.get("webpage_url"):
        lines.append(f"URL: {meta['webpage_url']}")
    if meta.get("chapters"):
        lines.append(f"Chapters: {len(meta['chapters'])}")
    desc = (meta.get("description") or "").strip()
    if desc:
        if len(desc) > 500:
            desc = desc[:500].rstrip() + "…"
        lines.append(f"Description: {desc}")
    return "\n".join(lines)


@mcp.tool()
def get_transcript(
    url: str,
    languages: list[str] | None = None,
    format: str = "text",
    preserve_formatting: bool = False,
    include_timestamps: bool = False,
    include_metadata: bool = True,
) -> str:
    """Fetch a YouTube video's transcript.

    Args:
        url: YouTube video URL or video ID
        languages: Preferred languages in priority order (e.g. ["en", "de"]). Defaults to English.
        format: Output format — one of: text, json, pretty, webvtt, srt
        preserve_formatting: Keep HTML formatting tags in the transcript text
        include_timestamps: When True with format="text", prefix each line with [HH:MM:SS]. Ignored for json/srt/webvtt/pretty (those formats already include timestamps).
        include_metadata: When True (default), prepend a [METADATA] block (title, channel, published, duration, views, description) before the transcript. Pass False for transcript-only output.
    """
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        return f"Error: {e}"

    langs = languages or ["en"]
    try:
        transcript = api.fetch(
            video_id,
            languages=langs,
            preserve_formatting=preserve_formatting,
        )
        if include_timestamps and format == "text":
            body = _format_transcript_with_timestamps(transcript)
        else:
            body = _format_transcript(transcript, format)
    except Exception as e:
        return _handle_transcript_error(e, video_id, langs)

    if not include_metadata:
        return body

    meta = _fetch_metadata(video_id)
    return f"{_format_metadata_block(meta)}\n\n[TRANSCRIPT]\n{body}"


@mcp.tool()
def summarize_transcript(
    url: str,
    prompt: str | None = None,
    languages: list[str] | None = None,
    include_timestamps: bool = False,
    include_metadata: bool = True,
) -> str:
    """Fetch a YouTube video's transcript and return it with summarization instructions.

    The LLM client should use the returned instructions and transcript to produce a summary.
    The output is structured into clearly-labeled sections so a human can review the prompt
    before letting the LLM act on it.

    Args:
        url: YouTube video URL or video ID
        prompt: Custom summarization instructions. If omitted, a default summary prompt is used.
        languages: Preferred languages in priority order (e.g. ["en", "de"]). Defaults to English.
        include_timestamps: When True, prefix each transcript line with [HH:MM:SS].
        include_metadata: When True (default), include a [VIDEO] block with title, channel, published date, duration, views, and description.
    """
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        return f"Error: {e}"

    langs = languages or ["en"]
    try:
        transcript = api.fetch(video_id, languages=langs)
        if include_timestamps:
            text = _format_transcript_with_timestamps(transcript)
        else:
            text = TextFormatter().format_transcript(transcript)
    except Exception as e:
        return _handle_transcript_error(e, video_id, langs)

    instructions = prompt or DEFAULT_SUMMARY_PROMPT
    prompt_source = "user-supplied" if prompt else "default"
    language = transcript.language
    language_code = transcript.language_code
    is_generated = transcript.is_generated

    sections = [
        f"[INSTRUCTIONS]\n{instructions}",
        f"[PROMPT_SOURCE]\n{prompt_source}",
    ]

    if include_metadata:
        meta = _fetch_metadata(video_id)
        sections.append(_format_metadata_block(meta, header="VIDEO"))

    sections.append(
        f"[METADATA]\n"
        f"Video ID: {video_id}\n"
        f"Language: {language} ({language_code})\n"
        f"Type: {'auto-generated' if is_generated else 'manual'}"
    )
    sections.append(f"[TRANSCRIPT]\n{text}")

    return "\n\n".join(sections)


@mcp.tool()
def get_video_metadata(url: str) -> str:
    """Fetch metadata (title, description, channel, upload date, duration, views, chapters, etc.) for a YouTube video.

    Args:
        url: YouTube video URL or video ID
    """
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        return f"Error: {e}"

    meta = _fetch_metadata(video_id)
    if meta is None:
        return f"Error: Failed to fetch metadata for video '{video_id}'."

    lines = [f"Metadata for video '{video_id}':", ""]
    if meta.get("title"):
        lines.append(f"Title: {meta['title']}")
    if meta.get("channel"):
        ch = meta["channel"]
        if meta.get("channel_url"):
            ch = f"{ch} ({meta['channel_url']})"
        lines.append(f"Channel: {ch}")
    pub = _format_upload_date(meta.get("upload_date"))
    if pub:
        lines.append(f"Published: {pub}")
    if meta.get("duration_seconds") is not None:
        lines.append(f"Duration: {_format_hms(meta['duration_seconds'])}")
    if meta.get("view_count") is not None:
        lines.append(f"Views: {meta['view_count']:,}")
    if meta.get("like_count") is not None:
        lines.append(f"Likes: {meta['like_count']:,}")
    if meta.get("age_limit"):
        lines.append(f"Age limit: {meta['age_limit']}")
    if meta.get("is_live"):
        lines.append("Live: yes")
    if meta.get("categories"):
        lines.append(f"Categories: {', '.join(meta['categories'])}")
    if meta.get("tags"):
        tags = meta["tags"][:20]
        suffix = "" if len(meta["tags"]) <= 20 else f" (+{len(meta['tags']) - 20} more)"
        lines.append(f"Tags: {', '.join(tags)}{suffix}")
    if meta.get("webpage_url"):
        lines.append(f"URL: {meta['webpage_url']}")
    if meta.get("thumbnail_url"):
        lines.append(f"Thumbnail: {meta['thumbnail_url']}")
    if meta.get("chapters"):
        lines.extend(["", "Chapters:"])
        for ch in meta["chapters"]:
            start = ch.get("start_time") or 0
            lines.append(f"  {_format_hms(start)} {ch.get('title', '')}")
    if meta.get("description"):
        lines.extend(["", "Description:", meta["description"]])
    return "\n".join(lines)


@mcp.tool()
def list_transcripts(url: str) -> str:
    """List available transcript languages for a YouTube video.

    Args:
        url: YouTube video URL or video ID
    """
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        return f"Error: {e}"

    try:
        transcript_list = api.list(video_id)
        lines = [f"Available transcripts for video '{video_id}':\n"]
        for t in transcript_list:
            kind = "auto-generated" if t.is_generated else "manual"
            translatable = "translatable" if t.is_translatable else "not translatable"
            lines.append(f"  - {t.language} ({t.language_code}) [{kind}, {translatable}]")
        if len(lines) == 1:
            return f"No transcripts found for video '{video_id}'."
        return "\n".join(lines)
    except Exception as e:
        return _handle_transcript_error(e, video_id, None)


if __name__ == "__main__":
    mcp.run()
