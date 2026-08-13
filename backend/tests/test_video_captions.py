"""Specifications for turning a video's WebVTT caption track into a plain
transcript of what is said.

A caption file is not a transcript: YouTube's automatic captions repeat each
line as the next one is spoken (a rolling window), carry per-word timing
markup inside the text, and describe sounds nobody said ("[Música]"). Feeding
that to a model verbatim triples the input and teaches it that the cook
repeated everything. These are pure functions over text — no network, no
model — and they return None when there is nothing usable, so the caller can
fall back to the video's written description (the same contract
recipe_json_ld uses).
"""

from pathlib import Path

from app.services.video_captions import transcript_from_vtt

FIXTURES = Path(__file__).parent / "fixtures"

AUTO_CAPTIONS = (FIXTURES / "youtube_auto_captions.vtt").read_text(encoding="utf-8")
HUMAN_SUBTITLES = (FIXTURES / "youtube_subtitles.vtt").read_text(encoding="utf-8")


def test_given_an_auto_generated_vtt_when_building_the_transcript_then_the_timing_markup_is_stripped() -> (
    None
):
    """Given automatic captions, whose text carries per-word timing markup
    (`<00:00:06.759><c> bolo</c>`), when building the transcript, then only the
    spoken words remain — no tags, no timestamps."""
    transcript = transcript_from_vtt(AUTO_CAPTIONS)

    assert transcript is not None
    assert "<" not in transcript
    assert "00:00:" not in transcript
    assert "bolo de cenoura" in transcript


def test_given_a_rolling_window_vtt_when_building_the_transcript_then_each_line_appears_once() -> (
    None
):
    """Given automatic captions that repeat the previous line in every cue,
    when building the transcript, then each spoken line appears exactly once —
    otherwise the model reads a recipe where every instruction was said
    twice."""
    transcript = transcript_from_vtt(AUTO_CAPTIONS)

    assert transcript is not None
    assert transcript.count("oi gente tudo bem hoje eu vou ensinar") == 1
    assert transcript.count("bate tudo no liquidificador e leva") == 1


def test_given_a_caption_line_that_grows_across_cues_when_building_the_transcript_then_only_the_complete_line_is_kept() -> (
    None
):
    """Given a line that arrives partially and is completed in the next cue
    ("médias três ovos" → "médias três ovos & duas xícaras de"), when building
    the transcript, then only the finished line is kept."""
    transcript = transcript_from_vtt(AUTO_CAPTIONS)

    assert transcript is not None
    assert "médias três ovos & duas xícaras de" in transcript
    assert "\nmédias três ovos\n" not in transcript


def test_given_a_vtt_when_building_the_transcript_then_the_spoken_order_is_preserved() -> None:
    """Given a caption track, when building the transcript, then its lines
    keep the order they were spoken in — a recipe read out of order would put
    the oven before the batter."""
    transcript = transcript_from_vtt(AUTO_CAPTIONS)

    assert transcript is not None
    assert transcript.index("oi gente") < transcript.index("três cenouras")
    assert transcript.index("três cenouras") < transcript.index("liquidificador")
    assert transcript.index("liquidificador") < transcript.index("180 graus")


def test_given_a_vtt_with_html_entities_when_building_the_transcript_then_they_are_unescaped() -> (
    None
):
    """Given captions carrying HTML entities (`&amp;`), which YouTube really
    does emit, when building the transcript, then they are decoded to the
    characters they stand for."""
    transcript = transcript_from_vtt(AUTO_CAPTIONS)

    assert transcript is not None
    assert "&amp;" not in transcript
    assert "três ovos & duas xícaras" in transcript


def test_given_a_vtt_with_sound_markers_when_building_the_transcript_then_they_are_left_out() -> (
    None
):
    """Given captions with bracketed sound descriptions ("[Música]",
    "[Aplausos]"), when building the transcript, then they are dropped — they
    are a caption-format artifact, not something the cook said."""
    transcript = transcript_from_vtt(AUTO_CAPTIONS)

    assert transcript is not None
    assert "[Música]" not in transcript
    assert "[Aplausos]" not in transcript


def test_given_a_human_written_vtt_when_building_the_transcript_then_its_sentences_are_returned() -> (
    None
):
    """Given subtitles written by the uploader — punctuated, accurate, with no
    rolling window — when building the transcript, then the sentences come
    back intact."""
    transcript = transcript_from_vtt(HUMAN_SUBTITLES)

    assert transcript is not None
    assert "Hoje vamos fazer um pudim de leite condensado." in transcript
    assert "1 lata de leite condensado, 3 ovos e 1 lata de leite." in transcript
    assert "Deixe esfriar antes de desenformar." in transcript


def test_given_a_vtt_with_cue_identifiers_and_notes_when_building_the_transcript_then_they_are_not_included() -> (
    None
):
    """Given a caption file with cue identifiers ("1", "cozinha-final") and a
    NOTE block, when building the transcript, then none of that structural
    text is mistaken for speech."""
    transcript = transcript_from_vtt(HUMAN_SUBTITLES)

    assert transcript is not None
    assert "Legendas revisadas" not in transcript
    assert "Não traduzir" not in transcript
    assert "cozinha-final" not in transcript
    assert "\n1\n" not in f"\n{transcript}\n"


def test_given_a_caption_file_whose_cues_are_not_blank_line_separated_when_building_the_transcript_then_the_speech_is_still_read() -> (
    None
):
    """Given a caption file that omits the blank line between cues — malformed
    per the spec, but a real thing tools emit — when building the transcript,
    then the speech is still read.

    A cue identifier can only open a cue block, so it is recognised by
    following a blank line as well as by preceding a timing line. Deciding on
    the lookahead alone would read every line of a file like this as an
    identifier and silently return nothing at all.
    """
    vtt = (
        "WEBVTT\n"
        "00:00:00.000 --> 00:00:02.000\n"
        "bate os ovos com o açúcar\n"
        "00:00:02.000 --> 00:00:04.000\n"
        "junta a farinha peneirada\n"
    )

    transcript = transcript_from_vtt(vtt)

    assert transcript is not None
    assert "bate os ovos com o açúcar" in transcript
    assert "junta a farinha peneirada" in transcript


def test_given_a_vtt_whose_only_cues_are_sound_markers_when_building_the_transcript_then_returns_none() -> (
    None
):
    """Given a caption track with music and applause but no speech — a Reel
    with a song over it and no narration — when building the transcript, then
    None is returned, so the caller falls back to the description or the
    audio instead of sending an empty transcript to a model."""
    vtt = (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:03.000\n[Música]\n\n"
        "00:00:03.000 --> 00:00:06.000\n[Aplausos]\n\n"
        "00:00:06.000 --> 00:00:09.000\n♪♪\n"
    )

    assert transcript_from_vtt(vtt) is None


def test_given_an_empty_or_unparseable_caption_file_when_building_the_transcript_then_returns_none() -> (
    None
):
    """Given an empty body, whitespace, or something that isn't a caption file
    at all (an error page served in place of the track), when building the
    transcript, then None is returned rather than garbage."""
    assert transcript_from_vtt("") is None
    assert transcript_from_vtt("   \n\n  ") is None
    assert transcript_from_vtt("<html><body>403 Forbidden</body></html>") is None


def test_given_any_vtt_when_building_the_transcript_then_no_timestamps_survive() -> None:
    """Given any caption track, when building the transcript, then no cue
    timing line survives — an invariant that holds for both caption styles."""
    for caption_text in (AUTO_CAPTIONS, HUMAN_SUBTITLES):
        transcript = transcript_from_vtt(caption_text)

        assert transcript is not None
        assert "-->" not in transcript
        assert "WEBVTT" not in transcript
