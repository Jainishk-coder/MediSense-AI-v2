# PDF Files for MediSense AI

Apni **12 disease PDFs** yahan rakho:

```
data/
  diabetes.pdf
  fever.pdf
  ...
```

Ya subfolder mein:

```
data/pdfs/
  diabetes.pdf
  heart_disease.pdf
  ...
```

Dono jagah se scan hoga.

## Rebuild knowledge base

PDFs add/update karne ke baad:

```bash
python build_db.py
python app.py
```

Yeh script sirf **PDF files** use karega — purane txt guides ab include nahi honge.

## Important

- PDF mein readable text hona chahiye (scanned image PDFs kaam nahi karenge bina OCR ke)
- Har rebuild ke baad app restart karo
