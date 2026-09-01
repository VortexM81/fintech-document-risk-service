from __future__ import annotations

import argparse
from pathlib import Path

from fintech_docs.infrai_client import InfraiClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Index one extracted policy document")
    parser.add_argument("document", type=Path, help="UTF-8 text extracted from a PDF")
    parser.add_argument("--collection", default="fintech-policies")
    args = parser.parse_args()

    client = InfraiClient()
    text = args.document.read_text(encoding="utf-8")
    chunks = [text[start : start + 1200] for start in range(0, len(text), 1200) if text[start : start + 1200].strip()]
    vectors = []
    for index, chunk in enumerate(chunks):
        vectors.append(
            {
                "id": f"{args.document.stem}-{index}",
                "embedding": client.embed(chunk),
                "metadata": {"text": chunk, "document_id": args.document.name},
            }
        )
    if not vectors:
        raise ValueError("Document contains no indexable text")
    client.create_collection(args.collection, len(vectors[0]["embedding"]))
    client.upsert(args.collection, vectors)
    print(f"indexed {len(vectors)} passages from {args.document.name}")


if __name__ == "__main__":
    main()
