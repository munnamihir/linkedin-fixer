import re
import time
import requests
import fitz
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

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
            return jsonify({"error": "Not enough data extracted. Use PDF upload instead."}), 400
        return jsonify({"profile": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("LinkedIn Fixer running at http://localhost:5001")
    app.run(port=5001, debug=False)
