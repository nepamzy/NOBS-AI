import pytest

from services.clipping.selector import _snap_to_word_boundary, _timestamped_transcript, select_clips
from services.clipping.transcription.engine import TranscriptResult, Word
from services.common.errors import ApprovalRequiredError


def _words():
    return [
        Word(word="Hello", start=0.0, end=0.4),
        Word(word="world", start=0.5, end=0.9),
        Word(word="this", start=10.0, end=10.3),
        Word(word="works", start=10.4, end=10.9),
    ]


def test_snap_to_word_boundary_never_lands_mid_word():
    words = _words()
    # A guess that lands squarely inside "world" (0.5-0.9) snaps to its
    # real start, never to some arbitrary point inside the word.
    assert _snap_to_word_boundary(0.7, words, "start") == 0.5
    assert _snap_to_word_boundary(0.75, words, "end") == 0.9


def test_timestamped_transcript_inserts_minute_second_markers():
    # _words() spans only 0.0-10.9s — inside one 15s marker interval, so
    # use a wider-spread list to actually exercise a second marker.
    words = [
        Word(word="Hello", start=0.0, end=0.4),
        Word(word="world", start=0.5, end=0.9),
        Word(word="later", start=20.0, end=20.5),
    ]
    text = _timestamped_transcript(words)
    assert "[00:00]" in text
    assert "[00:20]" in text
    assert "Hello world" in text
    assert "later" in text


def test_select_clips_raises_approval_required_when_unconfigured():
    transcript = TranscriptResult(full_text="hello world", words=_words())
    with pytest.raises(ApprovalRequiredError) as exc_info:
        select_clips(transcript, 3, llm_provider="", llm_api_key="", llm_model="claude-sonnet-5")
    assert "PAYMENT / COST WARNING" in str(exc_info.value)


def test_select_clips_snaps_llm_guesses_and_drops_degenerate_ones(monkeypatch):
    words = _words()
    transcript = TranscriptResult(full_text="hello world this works", words=words)

    class _Selection:
        def __init__(self, title, reason, start_seconds, end_seconds):
            self.title = title
            self.reason = reason
            self.start_seconds = start_seconds
            self.end_seconds = end_seconds

    class _Parsed:
        clips = [
            _Selection("Good clip", "reason", 0.6, 10.2),  # snaps to a real, non-degenerate range
            _Selection("Degenerate", "reason", 0.6, 0.65),  # both ends snap to the same word
        ]

    class _FakeResponse:
        parsed_output = _Parsed()

    class _FakeMessages:
        def parse(self, **kwargs):
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    results = select_clips(
        transcript, 2, llm_provider="anthropic", llm_api_key="key123", llm_model="claude-sonnet-5"
    )

    assert len(results) == 1
    assert results[0].title == "Good clip"
    assert results[0].start_seconds == 0.5  # snapped to "world"'s real start
    assert results[0].end_seconds == 10.3  # snapped to "this"'s real end
