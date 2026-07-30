import os
from pypdf import PdfReader
from docx import Document as DocxDocument


class DocumentLoader:

    @staticmethod
    def load(file_path: str) -> list[dict]:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return DocumentLoader._load_pdf(file_path)
        elif ext == ".txt":
            return DocumentLoader._load_txt(file_path)
        elif ext == ".docx":
            return DocumentLoader._load_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    @staticmethod
    def _load_pdf(file_path: str) -> list[dict]:
        reader = PdfReader(file_path)
        documents = []

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                documents.append({
                    "page_content": text.strip(),
                    "metadata": {"page": page_num + 1, "source": os.path.basename(file_path)},
                })

        return documents

    @staticmethod
    def _load_txt(file_path: str) -> list[dict]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return []

        return [{
            "page_content": content.strip(),
            "metadata": {"page": 1, "source": os.path.basename(file_path)},
        }]

    @staticmethod
    def _load_docx(file_path: str) -> list[dict]:
        doc = DocxDocument(file_path)
        full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

        if not full_text.strip():
            return []

        return [{
            "page_content": full_text.strip(),
            "metadata": {"page": 1, "source": os.path.basename(file_path)},
        }]
