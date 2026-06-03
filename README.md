# 🔧 LinkedIn Fixer

An open source AI tool that analyzes, scores, and rewrites your LinkedIn profile — free, local, no API keys needed.

![LinkedIn Fixer](https://img.shields.io/badge/AI-Powered-blue) ![Local](https://img.shields.io/badge/100%25-Local-green) ![Open Source](https://img.shields.io/badge/Open-Source-orange)

## What it does

- 📊 **Scores your profile** out of 100 with specific reasons
- 💡 **Suggests improvements** tailored to your background
- ✍️ **Rewrites your headline and summary** to be more compelling
- 🎯 **Gap analysis** against any job description you're targeting

## How it works

Upload your LinkedIn PDF (LinkedIn → More → Save to PDF), paste a job description, and get instant AI-powered feedback — all running locally on your machine via Ollama.

## Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com) running locally
- `llama3.2` model pulled (`ollama pull llama3.2`)

## Setup

```bash
# Clone the repo
git clone https://github.com/munnamihir/linkedin-fixer.git
cd linkedin-fixer

# Install dependencies
pip install flask flask-cors requests beautifulsoup4 pymupdf

# Pull the model
ollama pull llama3.2

# Start the app
python app.py
```

Then open `http://localhost:5001` in your browser.

## Usage

1. Go to LinkedIn → click **More** → **Save to PDF**
2. Open `http://localhost:5001`
3. Upload your PDF
4. (Optional) paste a job description for gap analysis
5. Click **Analyze & Fix My Profile**

## Tech stack

- Frontend: vanilla HTML/CSS/JS
- Backend: Python Flask
- AI: Ollama (llama3.2) — runs 100% locally, free, no API key
- PDF parsing: PyMuPDF

## Contributing

PRs welcome. Open an issue for bugs or feature requests.

## License

MIT
