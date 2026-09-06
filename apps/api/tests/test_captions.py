from services.rendering.ffmpeg.captions import build_cues, render_srt


def test_build_cues_offsets_words_onto_the_final_timeline():
    scene_one_words = [
        {"word": "Hello", "start": 0.0, "end": 0.3},
        {"word": "world", "start": 0.3, "end": 0.6},
    ]
    scene_two_words = [
        {"word": "Second", "start": 0.0, "end": 0.4},
        {"word": "scene", "start": 0.4, "end": 0.8},
    ]
    # scene one's voiceover measured 5.0s, so scene two starts at offset 5.0
    cues = build_cues([(0.0, scene_one_words), (5.0, scene_two_words)])

    assert len(cues) == 2
    assert cues[0].start_seconds == 0.0
    assert cues[0].end_seconds == 0.6
    assert cues[0].text == "Hello world"
    # scene two's words are shifted by its 5.0s offset, not left at 0
    assert cues[1].start_seconds == 5.0
    assert cues[1].end_seconds == 5.8
    assert cues[1].text == "Second scene"


def test_build_cues_never_blends_across_a_scene_boundary():
    # even a single short word in each scene must not merge into one cue,
    # since narration from different scenes shouldn't share a subtitle line
    scene_one_words = [{"word": "Hi", "start": 0.0, "end": 0.2}]
    scene_two_words = [{"word": "Bye", "start": 0.0, "end": 0.2}]
    cues = build_cues([(0.0, scene_one_words), (1.0, scene_two_words)])

    assert len(cues) == 2
    assert cues[0].text == "Hi"
    assert cues[1].text == "Bye"


def test_build_cues_splits_on_a_long_pause():
    words = [
        {"word": "First", "start": 0.0, "end": 0.3},
        # a >0.6s gap before the next word should start a new cue
        {"word": "Later", "start": 1.5, "end": 1.8},
    ]
    cues = build_cues([(0.0, words)])

    assert len(cues) == 2
    assert cues[0].text == "First"
    assert cues[1].text == "Later"


def test_build_cues_splits_on_word_count_cap():
    words = [{"word": f"w{i}", "start": i * 0.2, "end": i * 0.2 + 0.1} for i in range(10)]
    cues = build_cues([(0.0, words)])

    assert len(cues) == 2
    assert len(cues[0].text.split()) == 8
    assert len(cues[1].text.split()) == 2


def test_render_srt_formats_timestamps_and_indices():
    cues = build_cues([(0.0, [{"word": "Hi", "start": 0.0, "end": 1.5}])])
    srt = render_srt(cues)

    assert "1\n" in srt
    assert "00:00:00,000 --> 00:00:01,500" in srt
    assert "Hi" in srt
