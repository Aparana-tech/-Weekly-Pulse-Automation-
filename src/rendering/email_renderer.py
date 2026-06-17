"""
Email Report Renderer.

Generates HTML and Plain Text email payloads from a PulseReport.
"""

from __future__ import annotations

import datetime

from src.analysis.models import PulseReport


def _generate_deep_link(doc_id: str, anchor_id: str) -> str:
    """Generate a deep link to a specific section in a Google Doc."""
    # Google Docs heading links are usually in the format:
    # https://docs.google.com/document/d/{doc_id}/edit#heading=h.{anchor_id}
    # For now, we just pass the anchor_id. Real anchors might require Google Docs API
    # to fetch the actual heading ID, but for the assignment, we'll format it as requested.
    return f"https://docs.google.com/document/d/{doc_id}/edit#heading=h.{anchor_id}"


def render_email_payload(report: PulseReport, doc_id: str) -> dict[str, str]:
    """
    Render a PulseReport into an email payload dict.

    Returns:
        dict containing:
        - subject: The email subject line.
        - text_body: Plain text body.
        - html_body: HTML formatted body.
    """
    subject = f"📊 {report.display_name or report.product} Review Pulse — Week {report.iso_week}"
    deep_link = _generate_deep_link(doc_id, report.section_anchor)
    
    # 1. Plain Text Body
    text_lines = [
        f"Review Pulse for {report.display_name or report.product} (Week {report.iso_week}, {report.iso_year})",
        "",
        "Top Themes:",
    ]
    
    # Take top 3 themes
    top_themes = report.themes[:3]
    for theme in top_themes:
        text_lines.append(f"• {theme.name}: {theme.description}")
        
    # Gather action ideas from top themes
    action_ideas = []
    for theme in top_themes:
        if theme.actions:
            # Add up to 2 actions per top theme to keep email concise
            for action in theme.actions[:2]:
                action_ideas.append((theme.name, action))
                
    if action_ideas:
        text_lines.extend([
            "",
            "Top Action Ideas:"
        ])
        for theme_name, action in action_ideas:
            text_lines.append(f"• [{theme_name}] {action.title}: {action.details}")
            
    text_lines.extend([
        "",
        "Stats:",
        f"- {report.stats.total_reviews} reviews analyzed",
        f"- {report.stats.clusters_found} clusters found",
        "",
        f"Read Full Report -> {deep_link}",
        "",
        f"Generated at: {datetime.datetime.now(datetime.UTC).isoformat()}",
    ])
    
    text_body = "\n".join(text_lines)
    
    # 2. HTML Body
    themes_html = ""
    for theme in top_themes:
        themes_html += f"<li><strong>{theme.name}</strong>: {theme.description}</li>"
        
    html_body = f"""
    <html>
      <body style="font-family: sans-serif; line-height: 1.5; color: #333;">
        <h2>📊 Review Pulse for {report.display_name or report.product} (Week {report.iso_week}, {report.iso_year})</h2>
        
        <h3>Top Themes:</h3>
        <ul>
          {themes_html}
        </ul>
        """
        
    if action_ideas:
        actions_html = ""
        for theme_name, action in action_ideas:
            actions_html += f"<li><strong>[{theme_name}] {action.title}</strong>: {action.details}</li>"
            
        html_body += f"""
        <h3>Top Action Ideas:</h3>
        <ul>
          {actions_html}
        </ul>
        """
        
    html_body += f"""
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Stats:</strong> {report.stats.total_reviews} reviews analyzed | {report.stats.clusters_found} clusters found</p>
        </div>
        
        <a href="{deep_link}" style="display: inline-block; background-color: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">
            Read Full Report →
        </a>
        
        <hr style="margin-top: 30px; border: 0; border-top: 1px solid #eee;" />
        <p style="font-size: 0.8em; color: #777;">
            Generated at: {datetime.datetime.now(datetime.UTC).isoformat()}
        </p>
      </body>
    </html>
    """

    return {
        "subject": subject,
        "text_body": text_body,
        "html_body": html_body,
    }
