"""The one branded NOBS AI email template. Nobert's instruction: one solid
template to start, more can be added later once he's seen this one and
knows what he wants to tweak. Logo is referenced by its already-public
Vercel URL (the same file the app itself serves) rather than re-uploaded
anywhere — no attachment/inline-image handling needed.
"""

_LOGO_URL = "https://nobs-ai.vercel.app/logo-mark.png"

_HTML_TEMPLATE = """\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#0a0a0f;font-family:-apple-system,\
BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" \
style="background-color:#0a0a0f;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" \
style="max-width:560px;background-color:#111116;border-radius:12px;overflow:hidden;\
border:1px solid rgba(255,255,255,0.08);">
            <tr>
              <td style="padding:28px 32px 20px;border-bottom:1px solid rgba(255,255,255,0.08);">
                <img src="{logo_url}" alt="NOBS AI" width="28" height="28" \
style="display:inline-block;vertical-align:middle;" />
                <span style="display:inline-block;vertical-align:middle;margin-left:10px;\
font-size:17px;font-weight:700;color:#ffffff;letter-spacing:0.02em;">NOBS AI</span>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 32px;color:#e5e5ea;font-size:15px;line-height:1.6;">
                {body_html}
              </td>
            </tr>
            <tr>
              <td style="padding:20px 32px 28px;border-top:1px solid rgba(255,255,255,0.08);\
color:rgba(255,255,255,0.4);font-size:12px;">
                Sent via NOBS AI
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def render_branded_email(body_text: str) -> str:
    """Turns plain paragraphs (one per blank-line-separated block) into the
    branded HTML template. Kept deliberately simple — no markdown, no rich
    formatting — since this is for a quick draft Nobert reviews and can
    rewrite before sending, not a marketing campaign renderer."""
    paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip()]
    body_html = "".join(
        f"<p style='margin:0 0 16px;'>{p.replace(chr(10), '<br/>')}</p>" for p in paragraphs
    )
    return _HTML_TEMPLATE.format(logo_url=_LOGO_URL, body_html=body_html)
