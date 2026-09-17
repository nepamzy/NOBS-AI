from services.connectors.gmail.template import render_branded_email


def test_render_branded_email_includes_logo_and_branding():
    html = render_branded_email("Hello Nobert,\n\nThis is a test.")
    assert "NOBS AI" in html
    assert "https://nobs-ai.vercel.app/logo-mark.png" in html
    assert "<p style='margin:0 0 16px;'>Hello Nobert,</p>" in html
    assert "<p style='margin:0 0 16px;'>This is a test.</p>" in html


def test_render_branded_email_handles_empty_paragraphs():
    html = render_branded_email("\n\nJust one paragraph.\n\n")
    assert html.count("<p style=") == 1
