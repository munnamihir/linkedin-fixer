import re
import time
import io
import json
import requests
import fitz
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import inch

app = Flask(__name__, static_folder=".")
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    try:
        data = f.read()
        doc = fitz.open(stream=data, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        text = text.strip()
        if len(text) < 50:
            return jsonify({"error": "Could not extract text from PDF"}), 400
        return jsonify({"profile": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    if not url.startswith("http"):
        url = "https://" + url
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.get("https://www.linkedin.com", timeout=10)
        time.sleep(1)
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return jsonify({"error": f"LinkedIn returned {resp.status_code}. Use PDF upload instead."}), 400
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)[:4000]
        if len(text) < 100:
            return jsonify({"error": "Not enough data. Use PDF upload instead."}), 400
        return jsonify({"profile": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    try:
        data = request.json
        name = data.get("name", "LinkedIn Profile Analysis")
        score = data.get("score", 0)
        score_reason = data.get("score_reason", "")
        suggestions = data.get("suggestions", [])
        positives = data.get("positives", [])
        headline = data.get("headline", "")
        summary = data.get("summary", "")
        experience_tips = data.get("experience_tips", [])
        ats_score = data.get("ats_score", None)
        keywords_present = data.get("keywords_present", [])
        keywords_missing = data.get("keywords_missing", [])
        match_score = data.get("match_score", None)
        matching_skills = data.get("matching_skills", [])
        missing_skills = data.get("missing_skills", [])
        recommendations = data.get("recommendations", [])

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=0.75*inch, bottomMargin=0.75*inch)

        styles = getSampleStyleSheet()
        blue = HexColor("#0a66c2")
        dark = HexColor("#1d1d1d")
        muted = HexColor("#666666")
        green = HexColor("#057642")
        amber = HexColor("#b45309")
        red = HexColor("#c53030")

        title_style = ParagraphStyle("title", fontSize=22, textColor=blue, spaceAfter=4, fontName="Helvetica-Bold")
        sub_style = ParagraphStyle("sub", fontSize=11, textColor=muted, spaceAfter=16)
        h2_style = ParagraphStyle("h2", fontSize=14, textColor=blue, spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold")
        body_style = ParagraphStyle("body", fontSize=10, textColor=dark, spaceAfter=6, leading=15)
        bullet_style = ParagraphStyle("bullet", fontSize=10, textColor=dark, spaceAfter=5, leftIndent=16, leading=14)

        story = []

        # Header
        story.append(Paragraph("🔧 LinkedIn Fixer — Profile Analysis Report", title_style))
        story.append(Paragraph(f"Generated for: {name}", sub_style))
        story.append(HRFlowable(width="100%", thickness=1, color=blue))
        story.append(Spacer(1, 12))

        # Score
        story.append(Paragraph("Profile Score", h2_style))
        score_color = green if score >= 70 else amber if score >= 50 else red
        story.append(Paragraph(f"<font color='#{score_color.hexval()}' size='18'><b>{score}/100</b></font>", body_style))
        story.append(Paragraph(score_reason, body_style))
        story.append(Spacer(1, 8))

        # ATS Score
        if ats_score is not None:
            story.append(Paragraph("ATS Compatibility Score", h2_style))
            story.append(Paragraph(f"<b>{ats_score}/100</b>", body_style))
            if keywords_present:
                story.append(Paragraph("✅ Keywords Found:", body_style))
                story.append(Paragraph(", ".join(keywords_present), bullet_style))
            if keywords_missing:
                story.append(Paragraph("❌ Keywords Missing:", body_style))
                story.append(Paragraph(", ".join(keywords_missing), bullet_style))
            story.append(Spacer(1, 8))

        # Suggestions
        if suggestions:
            story.append(Paragraph("What to Improve", h2_style))
            for s in suggestions:
                story.append(Paragraph(f"⚠️  {s}", bullet_style))
            story.append(Spacer(1, 8))

        # Positives
        if positives:
            story.append(Paragraph("What's Already Working", h2_style))
            for p in positives:
                story.append(Paragraph(f"✅  {p}", bullet_style))
            story.append(Spacer(1, 8))

        # Rewrites
        story.append(Paragraph("Rewritten Sections", h2_style))
        if headline:
            story.append(Paragraph("<b>Headline:</b>", body_style))
            story.append(Paragraph(headline, bullet_style))
        if summary:
            story.append(Paragraph("<b>About / Summary:</b>", body_style))
            story.append(Paragraph(summary, bullet_style))
        if experience_tips:
            story.append(Paragraph("<b>Experience Tips:</b>", body_style))
            for t in experience_tips:
                story.append(Paragraph(f"💡  {t}", bullet_style))
        story.append(Spacer(1, 8))

        # Gap Analysis
        if match_score is not None:
            story.append(Paragraph("Job Match Analysis", h2_style))
            story.append(Paragraph(f"<b>Match Score: {match_score}%</b>", body_style))
            if matching_skills:
                story.append(Paragraph("✅ Matching Skills:", body_style))
                for s in matching_skills:
                    story.append(Paragraph(f"  • {s}", bullet_style))
            if missing_skills:
                story.append(Paragraph("❌ Missing Skills:", body_style))
                for s in missing_skills:
                    story.append(Paragraph(f"  • {s}", bullet_style))
            if recommendations:
                story.append(Paragraph("📌 Recommendations:", body_style))
                for r in recommendations:
                    story.append(Paragraph(f"  → {r}", bullet_style))

        doc.build(story)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
            as_attachment=True, attachment_filename="linkedin-analysis.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("LinkedIn Fixer running at http://localhost:5001")
    app.run(port=5001, debug=False)
