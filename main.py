"""
=============================================================
  Veille thematique & Newsletter Automatique - Agent Pipeline
  Sujet 05 - Master MPDAM 2024-2025
=============================================================

ARCHITECTURE :
  Agent 1 - Collecte & Resume   : NewsAPI -> articles -> resumes JSON
  Agent 2 - Selection & Ranking : score pertinence 0-10 -> top 5
  Agent 3 - Redaction HTML      : newsletter Jinja2 + objet accrocheur
  Action   - Envoi Gmail SMTP
"""

import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader
from groq import Groq

# -----------------------------------------
#  CONFIGURATION
# -----------------------------------------
NEWS_API_KEY    = "c376a015fd52492ca6c9b70a549a294b"
GROQ_API_KEY    = "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"
GMAIL_USER      = "benmstphaadem@gmail.com"
GMAIL_PASSWORD  = "tqsq wcei jrbl jirp"
RECIPIENT_EMAIL = "habibsmei@gmail.com"

MODEL         = "llama-3.3-70b-versatile"
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
OUTPUT_DIR    = Path("output")
TEMPLATE_DIR  = Path("templates")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)


# =============================================================
#  AGENT 1 - Collecte & Resume
# =============================================================
def agent1_collect_and_summarize(keyword: str) -> list[dict]:
    log.info(f"[Agent 1] Collecte des articles pour : '{keyword}'")

    params = {
        "q":        keyword,
        "language": "fr",
        "sortBy":   "publishedAt",
        "pageSize": 15,
        "apiKey":   NEWS_API_KEY,
    }
    resp = requests.get(NEWS_ENDPOINT, params=params, timeout=15)
    resp.raise_for_status()
    raw_articles = resp.json().get("articles", [])

    if not raw_articles:
        params["language"] = "en"
        resp = requests.get(NEWS_ENDPOINT, params=params, timeout=15)
        resp.raise_for_status()
        raw_articles = resp.json().get("articles", [])

    log.info(f"[Agent 1] {len(raw_articles)} articles recuperes.")

    summarized = []
    for art in raw_articles[:15]:
        title       = art.get("title", "Sans titre")
        url         = art.get("url", "")
        source      = art.get("source", {}).get("name", "Inconnu")
        published   = art.get("publishedAt", "")[:10]
        description = art.get("description") or art.get("content") or title

        prompt = (
            "Resume cet article en exactement 3 phrases. "
            "Chaque phrase doit faire moins de 20 mots. "
            "Reponds uniquement avec les 3 phrases, sans introduction ni commentaire.\n\n"
            f"Titre : {title}\n"
            f"Contenu : {description}"
        )

        message = client.chat.completions.create(
            model=MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = message.choices[0].message.content.strip()

        summarized.append({
            "title":        title,
            "url":          url,
            "source":       source,
            "published_at": published,
            "summary":      summary,
        })

    log.info("[Agent 1] Resumes generes avec succes.")
    return summarized


# =============================================================
#  AGENT 2 - Selection & Ranking
# =============================================================
def agent2_rank_and_select(articles: list[dict], keyword: str) -> list[dict]:
    log.info("[Agent 2] Scoring et selection des 5 meilleurs articles...")

    articles_json = json.dumps(
        [{"id": i, "title": a["title"], "summary": a["summary"]} for i, a in enumerate(articles)],
        ensure_ascii=False,
        indent=2,
    )

    prompt = (
        f"Evalue la pertinence de chaque article par rapport au theme '{keyword}'.\n\n"
        "Pour chaque article, attribue un score de 0 a 10 selon :\n"
        "- Actualite et nouveaute (0-3 pts)\n"
        "- Profondeur informative (0-4 pts)\n"
        "- Interet pour un public professionnel (0-3 pts)\n\n"
        "Reponds UNIQUEMENT avec un JSON valide, sans markdown ni backticks :\n"
        '[{"id": 0, "score": 8, "justification": "Texte court"}, ...]\n\n'
        f"Articles :\n{articles_json}"
    )

    message = client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.choices[0].message.content.strip()

    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()

    scored = json.loads(raw)

    id_to_score = {s["id"]: s for s in scored}
    for i, art in enumerate(articles):
        meta = id_to_score.get(i, {"score": 0, "justification": ""})
        art["score"]         = meta.get("score", 0)
        art["justification"] = meta.get("justification", "")

    top5 = sorted(articles, key=lambda x: x["score"], reverse=True)[:5]
    log.info(f"[Agent 2] Top 5 selectionne - scores : {[a['score'] for a in top5]}")
    return top5


# =============================================================
#  AGENT 3 - Redaction Newsletter
# =============================================================
def agent3_compose_newsletter(top5: list[dict], keyword: str) -> tuple[str, str, str]:
    log.info("[Agent 3] Redaction de la newsletter...")

    date_str = datetime.now().strftime("%d %B %Y")

    # Introduction : 2 phrases sobres
    intro_prompt = (
        f"Ecris une introduction de 2 phrases maximum pour une newsletter sur '{keyword}' du {date_str}. "
        "Ton sobre et professionnel. Indique que 5 articles ont ete selectionnes. "
        "Reponds uniquement avec les 2 phrases."
    )
    intro_msg = client.chat.completions.create(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": intro_prompt}],
    )
    intro = intro_msg.choices[0].message.content.strip()

    # CTA : 1 phrase courte
    cta_prompt = (
        f"Ecris une seule phrase de call-to-action pour une newsletter sur '{keyword}'. "
        "Ton direct et sobre. Pas d'emojis. Pas d'exclamations excessives."
    )
    cta_msg = client.chat.completions.create(
        model=MODEL,
        max_tokens=60,
        messages=[{"role": "user", "content": cta_prompt}],
    )
    cta = cta_msg.choices[0].message.content.strip()

    # Objet email
    subject_prompt = (
        f"Genere un objet d'email court et professionnel pour une newsletter sur '{keyword}' du {date_str}. "
        "Maximum 60 caracteres. Un seul emoji au debut. Reponds uniquement avec l'objet."
    )
    subject_msg = client.chat.completions.create(
        model=MODEL,
        max_tokens=60,
        messages=[{"role": "user", "content": subject_prompt}],
    )
    subject_line = subject_msg.choices[0].message.content.strip()

    # Rendu Jinja2
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("newsletter.html.j2")
    html = template.render(
        keyword=keyword,
        date=date_str,
        intro=intro,
        articles=top5,
        cta=cta,
        year=datetime.now().year,
    )

    log.info(f"[Agent 3] Newsletter redigee. Objet : {subject_line}")
    return html, subject_line, intro


# =============================================================
#  ACTION - Sauvegarde & Envoi Email
# =============================================================
def action_save_and_send(html: str, subject: str, keyword: str, send_email: bool = True) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = keyword.replace(" ", "_")[:30]
    filename = OUTPUT_DIR / f"newsletter_{slug}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"

    filename.write_text(html, encoding="utf-8")
    log.info(f"[Action] Newsletter sauvegardee : {filename}")

    if not send_email:
        log.info("[Action] Envoi email ignore (--no-email)")
        return str(filename)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_USER
        msg["To"]      = RECIPIENT_EMAIL
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())

        log.info(f"[Action] Email envoye a {RECIPIENT_EMAIL} - Objet : {subject}")
    except Exception as e:
        log.warning(f"[Action] Envoi email echoue : {e}")

    return str(filename)


# =============================================================
#  PIPELINE PRINCIPAL
# =============================================================
def run_pipeline(keyword: str, send_email: bool = True):
    log.info("=" * 60)
    log.info(f"  DEMARRAGE DU PIPELINE - Theme : '{keyword}'")
    log.info("=" * 60)

    all_articles = agent1_collect_and_summarize(keyword)

    OUTPUT_DIR.mkdir(exist_ok=True)
    raw_json_path = OUTPUT_DIR / "articles_bruts.json"
    raw_json_path.write_text(json.dumps(all_articles, ensure_ascii=False, indent=2), encoding="utf-8")

    top5 = agent2_rank_and_select(all_articles, keyword)

    top5_json_path = OUTPUT_DIR / "top5_selectionnes.json"
    top5_json_path.write_text(json.dumps(top5, ensure_ascii=False, indent=2), encoding="utf-8")

    html, subject, intro = agent3_compose_newsletter(top5, keyword)

    html_path = action_save_and_send(html, subject, keyword, send_email=send_email)

    log.info("=" * 60)
    log.info("  PIPELINE TERMINE AVEC SUCCES")
    log.info(f"  -> HTML      : {html_path}")
    log.info(f"  -> JSON brut : {raw_json_path}")
    log.info(f"  -> Top 5     : {top5_json_path}")
    log.info(f"  -> Objet     : {subject}")
    log.info("=" * 60)

    return {"html_path": html_path, "subject": subject, "top5": top5}


# -----------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Newsletter Agent Pipeline")
    parser.add_argument("keyword", help="Theme de la veille")
    parser.add_argument("--no-email", action="store_true", help="Ne pas envoyer l'email")
    args = parser.parse_args()

    run_pipeline(args.keyword, send_email=not args.no_email)