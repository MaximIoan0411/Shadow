"""Descarcă documentele oficiale din corpus/catalog.json și le salvează ca text în corpus/docs/.

    cd ai && uv run --extra corpus python -m rag.fetch

Se rulează o singură dată, cu internet (textele intră în git, ca demo-ul să meargă offline). Paginile NASA sunt
lucrări ale guvernului SUA (domeniu public); pagina CSA e reprodusă necomercial, cu sursa. Scrie și
corpus/sources.json: titlul și URL-ul fiecărui document, de unde vin citările.
"""
import io
import json
import re
import sys

import httpx

from .config import CATALOG_FILE, DOCS_DIR, SOURCES_FILE

# unele site-uri (CSA) închid conexiunea fără un User-Agent de browser
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) SHADOW-NASA-Space-Apps-2026/1.0 (educational corpus builder)"}
# secțiunea de bibliografie de la final nu ajută la răspunsuri: se taie
REFERENCES = re.compile(r"^\s*(?:[IVX]+\.|\d+(?:\.\d+)*\.?)?\s*(references|bibliography|literature cited)\s*:?\s*$", re.I | re.M)


def pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    pages = [page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages]
    text = "\n".join(pages)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # cuvinte despărțite la capăt de rând
    text = re.sub(r"^\s*\d{1,3}\s*$", "", text, flags=re.M)  # numere de pagină
    return text


def html_text(html: str, url: str) -> str:
    import trafilatura

    return trafilatura.extract(html, url=url, include_comments=False, include_tables=False, favor_recall=True) or ""


def cut_references(text: str) -> str:
    """Taie bibliografia, dacă începe în a doua jumătate a documentului."""
    matches = [m for m in REFERENCES.finditer(text) if m.start() > len(text) * 0.5]
    return text[: matches[-1].start()] if matches else text


def tidy(text: str) -> str:
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> int:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))["documents"]
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    sources, failed = [], []
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=60) as client:
        for doc in catalog:
            try:
                response = client.get(doc["url"])
                response.raise_for_status()
                is_pdf = "pdf" in response.headers.get("content-type", "") or doc["url"].lower().endswith(".pdf")
                text = pdf_text(response.content) if is_pdf else html_text(response.text, doc["url"])
                text = tidy(cut_references(text))
                if len(text.split()) < 80:
                    raise ValueError(f"prea puțin text ({len(text.split())} cuvinte)")
            except Exception as error:  # noqa: BLE001 — orice eroare: documentul se sare și se raportează
                failed.append((doc["id"], str(error)[:160]))
                print(f"  ✗ {doc['id']}: {error}", file=sys.stderr)
                continue
            (DOCS_DIR / f"{doc['id']}.txt").write_text(text + "\n", encoding="utf-8")
            sources.append({**doc, "file": f"docs/{doc['id']}.txt", "kind": "pdf" if is_pdf else "html", "words": len(text.split())})
            print(f"  ✓ {doc['id']}: {len(text.split())} cuvinte")
    SOURCES_FILE.write_text(json.dumps({"documents": sources}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(sources)} documente salvate, {len(failed)} sărite")
    return 0 if sources else 1


if __name__ == "__main__":
    sys.exit(main())
