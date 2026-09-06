from services.compliance.checker import check_script


def test_passes_with_no_prior_videos_and_clean_script():
    result = check_script(
        title="5 mistakes new developers make",
        hook="Here's what nobody tells you",
        scene_narrations=["Scene one narration.", "Scene two narration."],
        previous_titles=[],
    )
    assert result.passed is True
    assert result.blockers == []
    # the AI-disclosure reminder is always present, even on a clean pass
    assert any("disclosure" in w.lower() for w in result.warnings)


def test_blocks_near_duplicate_title():
    result = check_script(
        title="5 mistakes new developers make",
        hook="hook",
        scene_narrations=["narration"],
        previous_titles=["5 mistakes new developers make"],
    )
    assert result.passed is False
    assert len(result.blockers) == 1
    assert "similar to a previous video" in result.blockers[0]


def test_does_not_block_a_clearly_different_title():
    result = check_script(
        title="5 mistakes new developers make",
        hook="hook",
        scene_narrations=["narration"],
        previous_titles=["how volcanoes actually form"],
    )
    assert result.passed is True
    assert result.blockers == []


def test_flags_sensitive_topic_as_warning_not_a_block():
    result = check_script(
        title="A story about recovery",
        hook="hook",
        scene_narrations=["This story touches on self-harm and how she got through it."],
        previous_titles=[],
    )
    # storytelling can legitimately cover hard topics — never auto-blocked,
    # just surfaced for a human decision
    assert result.passed is True
    assert any("self-harm" in w.lower() for w in result.warnings)


def test_flags_financial_misinformation_pattern():
    result = check_script(
        title="Investing tips",
        hook="hook",
        scene_narrations=["This strategy offers guaranteed returns every time."],
        previous_titles=[],
    )
    assert any("financial misinformation" in w.lower() for w in result.warnings)
