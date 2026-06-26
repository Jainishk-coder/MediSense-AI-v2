"""
Build FAISS knowledge base from PDF files in the data folder.

Usage:
    python build_db.py

Put your disease PDFs in:
    data/           (directly)
    data/pdfs/      (subfolder)
    any subfolder under data/

After running, health_faiss_db/ will be created/updated.
"""

import json
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path("data")
OUTPUT_DIR = Path("health_faiss_db")
METADATA_FILE = DATA_DIR / "kb_metadata.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def find_pdf_files():
    pdfs = sorted(DATA_DIR.rglob("*.pdf"))
    return [p for p in pdfs if p.is_file()]


def load_documents(pdf_files):
    documents = []
    source_files = []

    for pdf_path in pdf_files:
        print(f"  Loading: {pdf_path.relative_to(DATA_DIR.parent)}")
        try:
            loader = PyPDFLoader(str(pdf_path))
            docs = loader.load()
            for doc in docs:
                doc.metadata["source_file"] = pdf_path.name
            documents.extend(docs)
            source_files.append(str(pdf_path.relative_to(DATA_DIR.parent)))
        except Exception as e:
            print(f"  WARNING: Could not load {pdf_path.name} — {e}")

    return documents, source_files


def main():
    print("=" * 52)
    print("  MediSense AI — Knowledge Base Builder")
    print("=" * 52)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/4] Scanning for PDF files in data/ ...")
    pdf_files = find_pdf_files()

    if not pdf_files:
        print("\n  ERROR: No PDF files found!")
        print("  Place your disease PDFs in:")
        print("    data/")
        print("    data/pdfs/")
        print("  Then run this script again.")
        return

    print(f"\n  Found {len(pdf_files)} PDF file(s)")

    print("\n[2/4] Loading PDF content...")
    documents, source_files = load_documents(pdf_files)

    if not documents:
        print("\n  ERROR: PDFs found but no text could be extracted.")
        return

    print(f"\n  Pages loaded: {len(documents)}")

    print("\n[3/4] Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    chunks = splitter.split_documents(documents)
    print(f"  Total chunks: {len(chunks)}")

    print("\n[4/4] Building FAISS index (may take 1-2 minutes)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(str(OUTPUT_DIR))

    metadata = {
        "source_count": len(source_files),
        "chunk_count": len(chunks),
        "source_files": source_files,
    }
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 52)
    print("  SUCCESS!")
    print(f"  PDF files : {len(source_files)}")
    print(f"  Chunks    : {len(chunks)}")
    print(f"  Saved to  : {OUTPUT_DIR}/")
    print("=" * 52)
    print("\n  Now run:  python app.py")


if __name__ == "__main__":
    main()
