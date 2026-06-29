"""
Build the MediSense AI FAISS knowledge base from PDF, TXT, and MD files.

Usage:
    python build_db.py

Place medical knowledge files anywhere under data/.
The script keeps the code simple and rebuilds health_faiss_db/ from scratch.
"""

import json
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path("data")
OUTPUT_DIR = Path("health_faiss_db")
METADATA_FILE = DATA_DIR / "kb_metadata.json"

CHUNK_SIZE = 950
CHUNK_OVERLAP = 180
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def find_source_files():
    files = []
    for path in sorted(DATA_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"kb_metadata.json", "README.md"}:
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


def load_text_document(path):
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    rel_path = str(path.relative_to(DATA_DIR.parent))
    return [
        Document(
            page_content=text,
            metadata={
                "source": rel_path,
                "source_file": path.name,
                "source_path": rel_path,
                "kind": "text_guide",
            },
        )
    ]


def load_pdf_documents(path):
    loader = PyPDFLoader(str(path))
    rel_path = str(path.relative_to(DATA_DIR.parent))
    docs = loader.load()
    for doc in docs:
        doc.metadata["source_file"] = path.name
        doc.metadata["source_path"] = rel_path
        doc.metadata["kind"] = "pdf"
    return docs


def load_documents(source_files):
    documents = []
    loaded_files = []

    for source_path in source_files:
        rel_path = str(source_path.relative_to(DATA_DIR.parent))
        print(f"  Loading: {rel_path}")
        try:
            if source_path.suffix.lower() == ".pdf":
                docs = load_pdf_documents(source_path)
            else:
                docs = load_text_document(source_path)

            if docs:
                documents.extend(docs)
                loaded_files.append(rel_path)
        except Exception as exc:
            print(f"  WARNING: Could not load {source_path.name} - {exc}")

    return documents, loaded_files


def main():
    print("=" * 56)
    print("  MediSense AI - Knowledge Base Builder")
    print("=" * 56)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/4] Scanning data/ for PDF, TXT, and MD files...")
    source_files = find_source_files()

    if not source_files:
        print("\n  ERROR: No knowledge files found.")
        print("  Add PDFs or text guides under data/ and run again.")
        return

    print(f"\n  Found {len(source_files)} source file(s)")

    print("\n[2/4] Loading content...")
    documents, loaded_files = load_documents(source_files)

    if not documents:
        print("\n  ERROR: Files were found but no text could be loaded.")
        return

    print(f"\n  Documents loaded: {len(documents)}")

    print("\n[3/4] Splitting into search chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    chunks = splitter.split_documents(documents)
    print(f"  Total chunks: {len(chunks)}")

    print("\n[4/4] Building FAISS index...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"local_files_only": True},
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(str(OUTPUT_DIR))

    metadata = {
        "source_count": len(loaded_files),
        "chunk_count": len(chunks),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "source_files": loaded_files,
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("\n" + "=" * 56)
    print("  SUCCESS")
    print(f"  Sources : {len(loaded_files)}")
    print(f"  Chunks  : {len(chunks)}")
    print(f"  Saved   : {OUTPUT_DIR}/")
    print("=" * 56)


if __name__ == "__main__":
    main()
