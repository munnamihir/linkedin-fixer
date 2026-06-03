import re
import time
import io
import requests
import fitz
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS


app = Flask(__name__, static_folder=".")
CORS(app)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def extract_pdf_text(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()

def parse_profile(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    p = {"name":"","headline":"","location":"","email":"","phone":"","linkedin":"","portfolio":"","summary":"","experience":[],"education":[],"skills":[],"certifications":[]}
    skip_words = ["http","@","+","www","linkedin","github","contact","summary","experience","education","skills","certification","top skills"]
    for line in lines:
        if not p["name"] and line and len(line) > 2 and len(line) < 60 and not any(x in line.lower() for x in skip_words):
            p["name"] = line
    try:
        ni = lines.index(p["name"])
        if ni+1 < len(lines): p["headline"] = lines[ni+1]
    except: pass
    for line in lines:
        if "@" in line and "." in line and "linkedin" not in line.lower() and not p["email"]: p["email"] = line
        if (line.startswith("+") or line.startswith("(")) and not p["phone"]: p["phone"] = line
        if "linkedin.com/in/" in line.lower() and not p["linkedin"]: p["linkedin"] = line
        if any(x in line for x in ["github.io","portfolio"]) and not p["portfolio"]: p["portfolio"] = line
        if any(x in line for x in ["Area","PA ","NY ","CA ","United States","India"]) and not p["location"]: p["location"] = line
    try:
        si = next(i for i,l in enumerate(lines) if "summary" in l.lower())
        sl = []
        for line in lines[si+1:si+15]:
            if any(x in line.lower() for x in ["experience","education","skills","certification"]): break
            sl.append(line)
        p["summary"] = " ".join(sl)
    except: pass
    try:
        ei = next(i for i,l in enumerate(lines) if l.lower()=="experience")
        i = ei+1
        while i < len(lines):
            line = lines[i]
            if any(x in line.lower() for x in ["education","skills","certification","top skills"]): break
            if i+1 < len(lines) and any(x in lines[i+1] for x in ["Engineer","Developer","Manager","Analyst","Designer","Intern","Lead"]):
                p["experience"].append({"company":line,"role":lines[i+1]if i+1<len(lines) else "","duration":lines[i+2]if i+2<len(lines) else "","location":lines[i+3]if i+3<len(lines) else ""})
                i += 4
            else: i += 1
    except: pass
    try:
        ei = next(i for i,l in enumerate(lines) if l.lower()=="education")
        i = ei+1
        while i < len(lines):
            line = lines[i]
            if any(x in line.lower() for x in ["skills","certification","experience"]): break
            if any(x in line for x in ["University","Institute","College","School"]):
                p["education"].append({"school":line,"degree":lines[i+1]if i+1<len(lines) else ""})
                i += 2
            else: i += 1
    except: pass
    try:
        ski = next(i for i,l in enumerate(lines) if "top skills" in l.lower())
        for line in lines[ski+1:ski+10]:
            if any(x in line.lower() for x in ["certification","experience","education"]): break
            p["skills"].append(line)
    except: pass
    try:
        ci = next(i for i,l in enumerate(lines) if "certification" in l.lower())
        for line in lines[ci+1:ci+10]:
            if any(x in line.lower() for x in ["experience","education","summary"]): break
            if line and len(line)>5: p["certifications"].append(line)
    except: pass
    return p

def score_color(s):
    if s >= 70: return "#057642"
    if s >= 50: return "#b45309"
    return "#c53030"

def score_label(s):
    if s >= 85: return "Excellent 🌟"
    if s >= 70: return "Good 👍"
    if s >= 50: return "Needs Work 🔧"
    return "Needs Fixes 🚨"

def make_items(lst, cls, icon):
    rows = []
    for x in lst:
        rows.append('<div class="item ' + cls + '"><span class="icon">' + icon + '</span>' + x + '</div>')
    return "".join(rows)

def make_keywords(lst, cls):
    return "".join('<span class="kw ' + cls + '">' + k + '</span>' for k in lst)

def score_ring(val, color, label):
    r = 45
    circ = 282.7
    offset = circ * (1 - val/100)
    return (
        '<div class="score-ring-wrap">'
        '<svg viewBox="0 0 110 110" width="110" height="110">'
        '<circle cx="55" cy="55" r="' + str(r) + '" fill="none" stroke="#eee" stroke-width="10"/>'
        '<circle cx="55" cy="55" r="' + str(r) + '" fill="none" stroke="' + color + '" stroke-width="10" '
        'stroke-linecap="round" stroke-dasharray="' + str(circ) + '" stroke-dashoffset="' + str(round(offset,1)) + '" '
        'transform="rotate(-90 55 55)"/>'
        '<text x="55" y="52" text-anchor="middle" font-size="18" font-weight="800" fill="' + color + '" font-family="sans-serif">' + str(val) + '</text>'
        '<text x="55" y="68" text-anchor="middle" font-size="9" fill="#888" font-family="sans-serif">' + label + '</text>'
        '</svg></div>'
    )

def build_html_report(data):
    name = data.get("name", "LinkedIn Profile")
    score = data.get("score", 0)
    ats = data.get("ats_score")
    ms = data.get("match_score")
    sc = score_color(score)
    reason = data.get("score_reason", "")
    suggestions = data.get("suggestions", [])
    positives = data.get("positives", [])
    headline = data.get("headline", "")
    summary = data.get("summary", "")
    tips = data.get("experience_tips", [])
    kp = data.get("keywords_present", [])
    km = data.get("keywords_missing", [])
    matching = data.get("matching_skills", [])
    missing = data.get("missing_skills", [])
    recs = data.get("recommendations", [])

    scores_html = score_ring(score, sc, "Profile")
    if ats is not None:
        scores_html += score_ring(ats, score_color(ats), "ATS")
    if ms is not None:
        scores_html += score_ring(ms, score_color(ms), "Job Match")

    positives_html = ""
    if positives:
        positives_html = '<div class="sub-label">What\'s Already Working</div>' + make_items(positives, "good", "✅")

    headline_html = ""
    if headline:
        headline_html = '<div class="rewrite-label">Headline</div><div class="rewrite-box">' + headline + '</div>'

    summary_html = ""
    if summary:
        summary_html = '<div class="rewrite-label">About / Summary</div><div class="rewrite-box">' + summary + '</div>'

    tips_html = ""
    if tips:
        tips_html = '<div class="rewrite-label">Experience Tips</div>' + make_items(tips, "rewrite", "💡")

    gap_html = ""
    if ms is not None:
        gap_html = (
            '<div class="section">'
            '<div class="section-header gap-header">🎯 Job Match Analysis</div>'
            '<div class="match-pct">' + str(ms) + '% match</div>'
            '<div class="progress-bar"><div class="progress-fill" style="width:' + str(ms) + '%;background:' + score_color(ms) + '"></div></div>'
            '<div class="sub-label">✅ Matching Skills</div>' + make_items(matching, "good", "✅") +
            '<div class="sub-label">❌ Missing Skills</div>' + make_items(missing, "gap", "❌") +
            '<div class="sub-label">📌 Recommendations</div>' + make_items(recs, "suggest", "→") +
            '</div>'
        )

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  @page { margin: 0; size: A4; }
  @media print { * { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: Arial, Helvetica, sans-serif; background: white; color: #1d1d1d; font-size: 13px; }
  .page { max-width: 780px; margin: 0 auto; background: white; }

  .header { background: linear-gradient(135deg, #004182, #0a66c2); padding: 28px 36px; color: white; }
  .brand { font-size: 11px; opacity: 0.7; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 10px; }
  .name { font-size: 26px; font-weight: 800; margin-bottom: 4px; }
  .tagline { font-size: 12px; opacity: 0.75; }

  .scores-section { padding: 24px 36px; border-bottom: 2px solid #f0f0f0; background: #fafafa; }
  .scores-row { display: flex; gap: 24px; align-items: center; }
  .score-ring-wrap { text-align: center; flex-shrink: 0; }
  .score-reason-box { flex: 1; padding-left: 20px; border-left: 3px solid #0a66c2; }
  .score-grade { font-size: 20px; font-weight: 800; margin-bottom: 6px; color: """ + sc + """; }
  .score-reason { font-size: 13px; color: #444; line-height: 1.6; }

  .section { padding: 20px 36px; border-bottom: 1px solid #eee; }
  .section-header { font-size: 13px; font-weight: 700; margin-bottom: 14px; padding: 7px 14px; border-radius: 6px; display: inline-block; }
  .suggest-header { background: #fef3c7; color: #92400e; }
  .rewrite-header { background: #dbeafe; color: #1e3a5f; }
  .keyword-header { background: #dcfce7; color: #14532d; }
  .gap-header { background: #ffedd5; color: #7c2d12; }

  .item { display: flex; align-items: flex-start; gap: 8px; padding: 9px 12px; border-radius: 7px; margin-bottom: 7px; font-size: 12.5px; line-height: 1.5; }
  .icon { flex-shrink: 0; }
  .suggest { background: #fffbeb; border-left: 3px solid #f59e0b; }
  .good { background: #f0fdf4; border-left: 3px solid #22c55e; }
  .gap { background: #fef2f2; border-left: 3px solid #ef4444; }
  .rewrite { background: #eff6ff; border-left: 3px solid #3b82f6; }

  .keyword-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
  .kw { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .kw-present { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
  .kw-missing { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }

  .sub-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #999; margin: 12px 0 7px; padding-bottom: 4px; border-bottom: 1px solid #eee; }

  .rewrite-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #999; margin-bottom: 6px; margin-top: 12px; }
  .rewrite-box { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 14px; font-size: 12.5px; line-height: 1.7; color: #1e3a5f; }

  .match-pct { font-size: 26px; font-weight: 800; margin-bottom: 8px; }
  .progress-bar { height: 8px; background: #eee; border-radius: 4px; overflow: hidden; margin-bottom: 14px; }
  .progress-fill { height: 100%; border-radius: 4px; }

  .footer { background: #004182; color: rgba(255,255,255,0.75); text-align: center; padding: 14px; font-size: 11px; }
</style>
</head>
<body>
<div class="page">

<div class="header">
  <div class="brand">🔧 LinkedIn Fixer — AI Profile Report</div>
  <div class="name">""" + name + """</div>
  <div class="tagline">AI-powered LinkedIn profile analysis</div>
</div>

<div class="scores-section">
  <div class="scores-row">
    """ + scores_html + """
    <div class="score-reason-box">
      <div class="score-grade">""" + score_label(score) + """</div>
      <div class="score-reason">""" + reason + """</div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-header keyword-header">🔍 Keyword Analysis</div>
  <div class="sub-label">Found in your profile</div>
  <div class="keyword-grid">""" + make_keywords(kp, "kw-present") + """</div>
  <div class="sub-label">Missing — add these</div>
  <div class="keyword-grid">""" + make_keywords(km, "kw-missing") + """</div>
</div>

<div class="section">
  <div class="section-header suggest-header">💡 What to Improve</div>
  """ + make_items(suggestions, "suggest", "⚠️") + positives_html + """
</div>

<div class="section">
  <div class="section-header rewrite-header">✍️ Rewritten Sections</div>
  """ + headline_html + summary_html + tips_html + """
</div>

""" + gap_html + """

<div class="footer">
  Generated by LinkedIn Fixer — github.com/munnamihir/linkedin-fixer — 100% free, local &amp; open source
</div>

</div>
</body>
</html>"""
    return html

@app.route("/")
def index(): return send_from_directory(".", "index.html")

@app.route("/health")
def health(): return jsonify({"status": "ok"})

@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files: return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    try:
        data = f.read()
        text = extract_pdf_text(data)
        if len(text) < 50: return jsonify({"error": "Could not extract text"}), 400
        return jsonify({"profile": text, "parsed": parse_profile(text)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url", "").strip()
    if not url: return jsonify({"error": "No URL"}), 400
    if not url.startswith("http"): url = "https://" + url
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        s.get("https://www.linkedin.com", timeout=10)
        time.sleep(1)
        r = s.get(url, timeout=15)
        if r.status_code != 200: return jsonify({"error": f"LinkedIn returned {r.status_code}. Use PDF instead."}), 400
        from bs4 import BeautifulSoup
        text = BeautifulSoup(r.text, "html.parser").get_text(separator=" ", strip=True)[:4000]
        if len(text) < 100: return jsonify({"error": "Not enough data."}), 400
        return jsonify({"profile": text, "parsed": parse_profile(text)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    try:
        html = build_html_report(request.json)
        return Response(html, mimetype="text/html")
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("LinkedIn Fixer running at http://localhost:5001")
    app.run(port=5001, debug=False)
