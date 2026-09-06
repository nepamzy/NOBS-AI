
from services.rendering.music_library import list_available_tracks, pick_track


def test_list_available_tracks_returns_empty_for_missing_folder(tmp_path):
    assert list_available_tracks(str(tmp_path / "does-not-exist")) == []


def test_list_available_tracks_filters_to_audio_files(tmp_path):
    (tmp_path / "song.mp3").write_bytes(b"")
    (tmp_path / "song.wav").write_bytes(b"")
    (tmp_path / "notes.txt").write_bytes(b"")
    (tmp_path / "cover.jpg").write_bytes(b"")

    tracks = list_available_tracks(str(tmp_path))
    assert tracks == ["song.mp3", "song.wav"]


def test_pick_track_returns_none_for_empty_library(tmp_path):
    assert pick_track(str(tmp_path), recently_used=[]) is None


def test_pick_track_avoids_recently_used_tracks(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"")
    (tmp_path / "b.mp3").write_bytes(b"")

    # a.mp3 was used in the last video — must not be picked again while b.mp3
    # (unused) is available
    for _ in range(10):
        assert pick_track(str(tmp_path), recently_used=["a.mp3"]) == "b.mp3"


def test_pick_track_reuses_the_least_recently_used_when_all_are_used(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"")
    (tmp_path / "b.mp3").write_bytes(b"")

    # both tracks used recently, "a.mp3" older (last in the most-recent-first
    # list) — reuse must prefer the staler one, not a fresh random pick
    result = pick_track(str(tmp_path), recently_used=["b.mp3", "a.mp3"])
    assert result == "a.mp3"


def test_pick_track_ignores_recently_used_entries_no_longer_in_the_library(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"")

    # "deleted.mp3" was used before but the file is gone now — must not crash,
    # and "a.mp3" (never used) should be picked
    assert pick_track(str(tmp_path), recently_used=["deleted.mp3"]) == "a.mp3"


def test_list_available_tracks_is_sorted(tmp_path):
    (tmp_path / "z.mp3").write_bytes(b"")
    (tmp_path / "a.mp3").write_bytes(b"")
    assert list_available_tracks(str(tmp_path)) == ["a.mp3", "z.mp3"]
