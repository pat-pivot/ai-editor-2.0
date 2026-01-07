"""
HTML Stripper for Email Deliverability

Converts rich HTML email templates to clean, deliverability-optimized format.
Matches n8n "Strip HTML for Deliverability" node exactly.

Created 1/2/26 for Step 4 HTML Compile migration.
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def strip_html_for_deliverability(stories: List[Dict[str, Any]], subject_line: str) -> str:
    """
    Convert decorated stories to clean, deliverability-optimized HTML.

    This matches the n8n "Strip HTML for Deliverability" node output.

    Deliverability optimizations:
    - Arial font family (no custom fonts)
    - No images
    - No external links (except unsubscribe)
    - Replaces "Pivot 5" with "Daily AI Briefing"
    - Simple bullet formatting with bullet character
    - Inline styles only
    - No complex CSS

    Args:
        stories: List of decorated story records from Airtable
        subject_line: Email subject line (used for leading headline)

    Returns:
        Clean HTML string optimized for deliverability
    """
    logger.info(f"[HTMLStripper] Stripping {len(stories)} stories for deliverability")

    # Start building clean HTML
    output_parts = []

    # Container with base styles
    output_parts.append(
        '<div style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.7; color: #333;">'
    )

    # Leading headline (matches n8n pattern)
    if stories:
        first_story = stories[0]
        fields = first_story.get('fields', {})
        leading_headline = fields.get('headline', '')
        if leading_headline:
            output_parts.append(
                f'<div style="font-size: 18px; font-weight: bold; color: #111; margin-bottom: 24px;">{_escape_html(leading_headline)}</div>'
            )

    # Build each story block
    for i, story in enumerate(stories):
        fields = story.get('fields', {})

        # Topic label
        label = fields.get('label', '')
        if label:
            output_parts.append(
                f'<div style="font-size: 12px; font-weight: bold; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{_escape_html(label)}</div>'
            )

        # Headline
        headline = fields.get('headline', '')
        if headline:
            output_parts.append(
                f'<div style="font-size: 16px; font-weight: 600; color: #111; margin-bottom: 12px;">{_escape_html(headline)}</div>'
            )

        # Bullet points - check both field naming conventions:
        # - Decoration table uses: b1, b2, b3
        # - Some code references: ai_bullet_1, ai_bullet_2, ai_bullet_3
        for idx in range(1, 4):
            # Try b1/b2/b3 first (Decoration table), then ai_bullet_X fallback
            bullet = fields.get(f'b{idx}', '') or fields.get(f'ai_bullet_{idx}', '')
            if bullet:
                # Clean bullet text (preserve bold tags from decoration)
                bullet_clean = _escape_html(bullet.strip(), preserve_bold=True)
                output_parts.append(
                    f'<div style="margin-bottom: 10px; padding-left: 16px;">\u2022 {bullet_clean}</div>'
                )

        # Separator between stories (not after last story)
        if i < len(stories) - 1:
            output_parts.append(
                '<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;">'
            )

    # Footer with unsubscribe
    output_parts.append(
        '<div style="font-size: 12px; color: #888; margin-top: 20px;">'
        "You're receiving this because you subscribed to our daily AI briefing.<br>"
        "Unsubscribe: {{unsubscribe_url}}"
        "</div>"
    )

    # Close container
    output_parts.append("</div>")

    # Join all parts
    html = "\n".join(output_parts)

    # Replace "Pivot 5" with "Daily AI Briefing" for deliverability
    html = re.sub(r'Pivot\s*5', 'Daily AI Briefing', html, flags=re.IGNORECASE)

    logger.info(f"[HTMLStripper] Generated {len(html)} chars of clean HTML")
    return html


def _escape_html(text: str, preserve_bold: bool = True) -> str:
    """
    Escape HTML special characters, optionally preserving bold tags.

    Args:
        text: Text to escape
        preserve_bold: If True, preserve <b> and </b> tags (default True)

    Returns:
        HTML-escaped text with bold tags preserved if requested
    """
    if not text:
        return ""

    if preserve_bold:
        # Temporarily replace bold tags with placeholders
        text = text.replace('<b>', '___BOLD_OPEN___')
        text = text.replace('</b>', '___BOLD_CLOSE___')

    # Escape HTML special characters
    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

    if preserve_bold:
        # Restore bold tags
        text = text.replace('___BOLD_OPEN___', '<b>')
        text = text.replace('___BOLD_CLOSE___', '</b>')

    return text


def build_full_html_email(
    stories: List[Dict[str, Any]],
    subject_line: str,
    summary: str = "",
    include_images: bool = True
) -> str:
    """
    Build the complete responsive HTML email template.

    This is the rich version with images and full styling.
    Use strip_html_for_deliverability() for Mautic sends.

    Args:
        stories: List of decorated story records
        subject_line: Email subject line
        summary: Short summary for preheader
        include_images: Whether to include story images

    Returns:
        Full responsive HTML email
    """
    from datetime import datetime

    year = datetime.now().year
    preheader = summary or subject_line

    # Build story blocks
    story_blocks = []
    for story in stories:
        fields = story.get('fields', {})

        # Image block
        # IMPORTANT: Image is placed inside td, so use div wrapper not tr/td
        # The outer structure already has <tr><td>, so we just need content
        image_html = ""
        if include_images:
            image_url = fields.get('image_url', '')
            if image_url:
                image_html = f'''
    <div style="padding:0 0 12px 0;">
      <img src="{image_url}" alt="" style="width:100%; height:auto; border-radius:6px; display:block;" />
    </div>'''

        # Bullets HTML - check both field naming conventions:
        # - Decoration table uses: b1, b2, b3
        # - Some code references: ai_bullet_1, ai_bullet_2, ai_bullet_3
        bullets_parts = []
        for idx in range(1, 4):
            # Try b1/b2/b3 first (Decoration table), then ai_bullet_X fallback
            bullet = fields.get(f'b{idx}', '') or fields.get(f'ai_bullet_{idx}', '')
            if bullet:
                bullets_parts.append(
                    f'<div style="margin-bottom:10px; padding-left:12px; font-size:14px; line-height:1.6; color:#4b5563;">\u2022 {_escape_html(bullet, preserve_bold=True)}</div>'
                )
        bullets_html = "\n".join(bullets_parts)

        # Story URL
        url = fields.get('pivotnews_url', '#')

        story_block = f'''
<tr>
  <td style="padding:20px 22px; border-bottom:1px solid #e5e7eb;">
    <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.14em; color:#9ca3af; padding-bottom:6px;">
      {_escape_html(fields.get('label', 'AI NEWS'))}
    </div>
    <div style="font-size:20px; line-height:1.4; font-weight:600; color:#0f172a; padding-bottom:10px;">
      <a href="{url}" style="color:#0f172a; text-decoration:none;">
        {_escape_html(fields.get('headline', ''))}
      </a>
    </div>
    {image_html}
    {bullets_html}
    <div style="font-size:13px; color:#4b5563; padding-top:10px;">
      Read More <a href="{url}" style="color:#f97316; text-decoration:underline;">Here</a>.
    </div>
  </td>
</tr>'''
        story_blocks.append(story_block)

    story_blocks_html = "\n".join(story_blocks)

    # Full email template
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(subject_line)}</title>
  <style>
    body {{ margin: 0; padding: 0; background-color: #f3f4f6; }}
    table {{ border-collapse: collapse; }}
    img {{ border: 0; max-width: 100%; height: auto; display: block; }}
    .wrapper {{ width: 640px; max-width: 100%; }}
    @media only screen and (max-width: 640px) {{
      .wrapper {{ width: 100% !important; }}
      .stack {{ display: block !important; width: 100% !important; }}
    }}
  </style>
</head>
<body style="margin:0; padding:0; background-color:#f3f4f6;">
  <!-- Hidden preheader -->
  <div style="display:none; max-height:0; overflow:hidden; opacity:0; font-size:1px; line-height:1px; color:#f3f4f6;">
    {_escape_html(preheader)}
  </div>

  <center style="width:100%; background-color:#f3f4f6;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" class="wrapper" cellspacing="0" cellpadding="0" border="0" style="background-color:#f3f4f6;">

            <!-- Header with logo -->
            <tr>
              <td style="padding:0 0 16px 0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="center" style="padding:0 12px;">
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#ffffff;">
                        <tr>
                          <td style="padding:18px 22px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                              <tr>
                                <td style="width:37%;"></td>
                                <td style="width:34%; text-align:center; vertical-align:middle;">
                                  <img src="https://img.pivotnews.com/cdn-cgi/imagedelivery/KXy14RehLGC3ziMxzD_shA/8423e6dd-0804-45f0-d570-e595634da200/logo" alt="Pivot 5" style="display:block; margin:0 auto; max-width:180px; height:auto;" />
                                </td>
                                <td style="width:29%;"></td>
                              </tr>
                              <tr>
                                <td colspan="3" style="padding-top:10px;">
                                  <div style="margin:0 auto; max-width:520px; text-align:center; font-size:15px; line-height:1.5; color:#4b5563;">
                                    The must-read daily AI briefing for over 1 million busy professionals who need signal, not noise.
                                  </div>
                                  <div style="margin:4px auto 0 auto; max-width:520px; text-align:center; font-size:15px; line-height:1.5; color:#4b5563; font-style:italic;">
                                    5 headlines. 5 minutes. 5 days a week.
                                  </div>
                                </td>
                              </tr>
                            </table>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Story blocks -->
            <tr>
              <td style="padding:0 12px 24px 12px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#ffffff; border:1px solid #e5e7eb;">
                  {story_blocks_html}
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:0 12px 24px 12px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%; background-color:#f9fafb; border:1px solid #e5e7eb;">
                  <tr>
                    <td style="padding:12px 16px; font-size:11px; line-height:1.6; color:#6b7280;">
                      You're receiving this email because you subscribed to Pivot 5.<br />
                      <a href="{{{{unsubscribe_url}}}}" style="color:#4b5563; text-decoration:underline;">Unsubscribe</a> &bull;
                      <a href="{{{{manage_prefs_url}}}}" style="color:#4b5563; text-decoration:underline;">Manage preferences</a>
                    </td>
                    <td align="right" style="padding:12px 16px; font-size:11px; color:#6b7280; white-space:nowrap;">
                      &copy; {year} Pivot 5
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </center>
</body>
</html>'''

    logger.info(f"[HTMLStripper] Generated full HTML email: {len(html)} chars")
    return html
