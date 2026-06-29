# PDF Files for MediSense AI

Place disease or health PDFs in either location:

```text
data/
  diabetes.pdf
  pneumonia.pdf

data/pdfs/
  heart_health.pdf
  first_aid.pdf
```

The knowledge builder scans PDFs, TXT files, and MD files from the full `data/` folder.

After adding or updating knowledge files, run:

```bash
python build_db.py
python app.py
```

Important:

- PDFs should contain selectable text.
- Scanned image PDFs need OCR first.
- Restart the Flask app after rebuilding the FAISS database.
