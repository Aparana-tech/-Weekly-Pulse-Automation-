import asyncio
import json
from src.config.settings import Settings
from src.analysis.pipeline import analyze_reviews
from src.ingestion.models import Review
from src.rendering.email_renderer import render_email_payload
from src.rendering.docs_renderer import render_docs_payload

async def main():
    settings = Settings(embedding_model="all-MiniLM-L6-v2", llm_model="llama-3.3-70b-versatile")
    
    with open("downloads/groww_2026_W25_reviews.json") as f:
        data = json.load(f)
        reviews = [Review(**r) for r in data]
        
    report = await analyze_reviews(reviews, settings)
    
    with open("groq_report.md", "w") as f:
        f.write("# Groq Analysis Output\n\n")
        f.write("## Top Themes\n")
        for i, theme in enumerate(report.themes, 1):
            f.write(f"### {i}. {theme.name} ({theme.review_count} reviews)\n")
            f.write(f"{theme.description}\n\n")
            f.write("**Quotes:**\n")
            for q in theme.validated_quotes:
                f.write(f"- \"{q.text}\" ({q.rating} stars)\n")
            
            f.write("\n**Action Ideas:**\n")
            for a in theme.actions:
                f.write(f"- {a.title}: {a.details}\n")
            f.write("\n---\n\n")

    email_payload = render_email_payload(report, doc_id="test_doc_id_123")
    with open("groq_email_preview.html", "w") as f:
        f.write(email_payload["html_body"])
        
    with open("email_teaser.json", "w") as f:
        json.dump(email_payload, f, indent=2)
        
    docs_payload = render_docs_payload(report)
    with open("docs_section.json", "w") as f:
        json.dump(docs_payload, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
