# MediSense AI

MediSense AI is a medical information chatbot built with Retrieval-Augmented Generation (RAG). It helps users understand symptoms, common conditions, prevention, safe self-care, and when they should consult a doctor.

This project is for educational use only. It does not replace professional medical advice, diagnosis, or treatment.

## Features

- Symptom-aware health chatbot
- English and Hindi/Hinglish response support
- RAG pipeline with LangChain, FAISS, and HuggingFace embeddings
- Groq Llama 3.3 powered answer generation
- Expanded medical knowledge base from PDFs, TXT, and MD files
- Emergency and doctor-visit triage badges
- Chat history with SQLite
- Responsive modern UI
- Knowledge base status panel
- Copy response action

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python, Flask
- AI/RAG: LangChain, FAISS, HuggingFace Embeddings, Groq API
- Database: SQLite

## How It Works

1. The user enters symptoms or a health question.
2. Flask receives the message and detects language and care level.
3. LangChain retrieves relevant chunks from the FAISS knowledge base.
4. The retrieved context is passed to the LLM with a safe medical prompt.
5. MediSense AI returns an educational answer with self-care and doctor-visit guidance.
6. The conversation is saved locally in SQLite.

## Project Structure

```text
MediSense-AI/
  data/
    health_guides/
    pdfs/
    kb_metadata.json
  health_faiss_db/
  static/
    logo.svg
    script.js
    style.css
  templates/
    index.html
  app.py
  build_db.py
  db.py
  requirements.txt
  README.md
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Rebuild the knowledge base after adding or editing files inside `data/`:

```bash
python build_db.py
```

Run the app:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Knowledge Base

The builder scans these formats anywhere under `data/`:

- `.pdf`
- `.txt`
- `.md`

The project includes disease PDFs plus expanded text guides for fever, cough, diabetes, hypertension, digestive issues, emergencies, pregnancy safety, child red flags, mental health, skin, kidney/urinary symptoms, and prevention.

## Safety Design

MediSense AI is designed to:

- Avoid confirming diagnoses
- Avoid prescribing medicines or dosages
- Highlight emergency symptoms
- Encourage doctor consultation for red flags
- Ask follow-up questions when symptoms are incomplete

## Author

Jainish Kandoliya  
Aspiring AI/ML Engineer | B.Tech CSE

- LinkedIn: https://www.linkedin.com/in/kandoliya-jainish
- GitHub: https://github.com/Jainishk-coder

## License

MIT License
