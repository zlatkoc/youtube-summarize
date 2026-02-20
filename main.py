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


@mcp.tool()
def get_transcript(
    url: str,
    languages: list[str] | None = None,
    format: str = "text",
    preserve_formatting: bool = False,
) -> str:
    """Fetch a YouTube video's transcript.

    Args:
        url: YouTube video URL or video ID
        languages: Preferred languages in priority order (e.g. ["en", "de"]). Defaults to English.
        format: Output format — one of: text, json, pretty, webvtt, srt
        preserve_formatting: Keep HTML formatting tags in the transcript text
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
        return _format_transcript(transcript, format)
    except Exception as e:
        return _handle_transcript_error(e, video_id, langs)


@mcp.tool()
def summarize_transcript(
    url: str,
    prompt: str | None = None,
    languages: list[str] | None = None,
) -> str:
    """Fetch a YouTube video's transcript and return it with summarization instructions.

    The LLM client should use the returned instructions and transcript to produce a summary.

    Args:
        url: YouTube video URL or video ID
        prompt: Custom summarization instructions. If omitted, a default summary prompt is used.
        languages: Preferred languages in priority order (e.g. ["en", "de"]). Defaults to English.
    """
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        return f"Error: {e}"

    langs = languages or ["en"]
    try:
        transcript = api.fetch(video_id, languages=langs)
        text = TextFormatter().format_transcript(transcript)

        instructions = prompt or DEFAULT_SUMMARY_PROMPT
        language = transcript.language
        language_code = transcript.language_code
        is_generated = transcript.is_generated

        return (
            f"[INSTRUCTIONS]\n{instructions}\n\n"
            f"[METADATA]\n"
            f"Video ID: {video_id}\n"
            f"Language: {language} ({language_code})\n"
            f"Type: {'auto-generated' if is_generated else 'manual'}\n\n"
            f"[TRANSCRIPT]\n{text}"
        )
    except Exception as e:
        return _handle_transcript_error(e, video_id, langs)


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
