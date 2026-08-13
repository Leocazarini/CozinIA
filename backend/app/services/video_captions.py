"""Turns a WebVTT caption track into a plain transcript of what is said.

Pure functions over text, and the video flow's counterpart to
recipe_json_ld: both take a structured file a platform already publishes and
render it as plain text, and both return None on a miss so the caller can
fall back to something else — the description, or the video's audio.

A caption file is not a transcript. YouTube's automatic captions repeat the
previous line in every cue as a rolling window, carry per-word timing markup
inside the text, and describe sounds nobody said. Handing that to a model
verbatim triples the input and reads as if the cook repeated every step.
"""

import html
import re

# Covers both `<00:00:06.759>` timing markers and the `<c>`/`<c.colorE5E5E5>`
# spans YouTube wraps each word in — same approach as recipe_json_ld's tag
# strip, since in both cases the markup is noise and the inner text is what
# matters.
_MARKUP_RE = re.compile(r"<[^>]+>")

# "[Música]", "[Aplausos]", "[risos]" and bare musical notes: a caption-format
# convention for sounds, not speech. Dropped structurally here so the model
# never has to be told to ignore them.
_SOUND_MARKER_RE = re.compile(r"\[[^\]]*\]|♪+")

_WHITESPACE_RE = re.compile(r"\s+")

_CUE_TIMING_MARKER = "-->"
_HEADER_PREFIXES = ("WEBVTT", "Kind:", "Language:")
_NOTE_KEYWORD = "NOTE"


def transcript_from_vtt(caption_text: str) -> str | None:
    """Return the spoken text of a WebVTT `caption_text`, or None when it
    holds nothing usable.

    None means "no speech here": an empty body, something that isn't a caption
    file at all (an error page served in place of the track), or a track whose
    every cue is a sound marker — a Reel with a song over it and no narration.
    The caller falls back rather than sending an empty transcript to a model.
    """
    # The spec requires a WebVTT file to open with this signature, which makes
    # it the cheap way to tell a caption track from whatever else a CDN might
    # have answered with — an expired-link error page reads as plausible text
    # otherwise, and would be sent on as if the cook had said it.
    if not caption_text.lstrip().startswith("WEBVTT"):
        return None

    lines = caption_text.splitlines()
    transcript: list[str] = []

    for index, raw_line in enumerate(lines):
        if _is_structural(raw_line, lines, index):
            continue

        line = _clean_line(raw_line)
        if not line:
            continue

        _append_deduplicated(transcript, line)

    return "\n".join(transcript) or None


def _is_structural(raw_line: str, lines: list[str], index: int) -> bool:
    """Whether `raw_line` is part of the caption file's structure rather than
    something that was said."""
    line = raw_line.strip()
    if not line:
        return True
    if _CUE_TIMING_MARKER in line:
        return True
    if line.startswith(_HEADER_PREFIXES):
        return True
    if _is_in_note_block(lines, index):
        return True
    return _is_cue_identifier(lines, index)


def _is_in_note_block(lines: list[str], index: int) -> bool:
    """Whether the line at `index` belongs to a NOTE comment block, which runs
    from the NOTE keyword to the next blank line."""
    for previous in reversed(lines[:index]):
        if not previous.strip():
            return False
        if previous.strip().startswith(_NOTE_KEYWORD):
            return True
    return False


def _is_cue_identifier(lines: list[str], index: int) -> bool:
    """Whether the line at `index` is a cue identifier — the optional label a
    cue may carry on the line directly above its timing.

    Recognised by position, not by the label's shape: a rule like "a single
    word on its own line" would also swallow a legitimate one-word caption
    ("cenoura"). Two conditions, because an identifier both opens a cue block
    (so it follows a blank line) and introduces its timing (so a timing line
    comes next). Requiring only the second would read every line of a file
    whose cues are not blank-line separated as an identifier, and return an
    empty transcript for a caption track that is merely malformed.
    """
    if index > 0 and lines[index - 1].strip():
        return False

    for following in lines[index + 1 :]:
        if not following.strip():
            return False
        return _CUE_TIMING_MARKER in following
    return False


def _clean_line(raw_line: str) -> str:
    """Strip a caption line down to the words that were spoken."""
    line = _MARKUP_RE.sub("", raw_line)
    line = html.unescape(line)
    line = _SOUND_MARKER_RE.sub("", line)
    return _WHITESPACE_RE.sub(" ", line).strip()


def _append_deduplicated(transcript: list[str], line: str) -> None:
    """Append `line` unless it is the rolling window repeating itself.

    Two rules, both against the last line kept: an identical line is the
    previous cue being redisplayed, and a prefix relationship is one line
    growing in place as more words are recognised — there, the longer version
    replaces the shorter one.

    Known cost: genuinely repeated speech across cues ("bate bate") collapses
    into one. Acceptable, since the model pass downstream is what turns this
    into prose anyway.
    """
    if not transcript:
        transcript.append(line)
        return

    previous = transcript[-1]
    if line == previous:
        return
    if line.startswith(previous):
        transcript[-1] = line
        return
    if previous.startswith(line):
        return

    transcript.append(line)
