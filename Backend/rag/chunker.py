try:
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,
        CharacterTextSplitter,
        MarkdownHeaderTextSplitter,
    )
except ImportError:
    from langchain.text_splitter import (
        RecursiveCharacterTextSplitter,
        CharacterTextSplitter,
        MarkdownHeaderTextSplitter,
    )


class TextChunker:

    STRATEGIES = ["recursive", "fixed_size", "sentence", "markdown"]

    @staticmethod
    def chunk(
        documents: list[dict],
        strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[dict]:
        if strategy not in TextChunker.STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}. Use one of: {TextChunker.STRATEGIES}")

        texts = [doc["page_content"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]

        if strategy == "recursive":
            return TextChunker._recursive_split(texts, metadatas, chunk_size, chunk_overlap)
        elif strategy == "fixed_size":
            return TextChunker._fixed_size_split(texts, metadatas, chunk_size, chunk_overlap)
        elif strategy == "sentence":
            return TextChunker._sentence_split(texts, metadatas, chunk_size, chunk_overlap)
        elif strategy == "markdown":
            return TextChunker._markdown_split(texts, metadatas)

    @staticmethod
    def _recursive_split(texts, metadatas, chunk_size, chunk_overlap):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks = []
        for text, metadata in zip(texts, metadatas):
            splits = splitter.split_text(text)
            for i, split in enumerate(splits):
                chunks.append({
                    "chunk_text": split,
                    "metadata": {**metadata, "chunk_index": i},
                })
        return chunks

    @staticmethod
    def _fixed_size_split(texts, metadatas, chunk_size, chunk_overlap):
        splitter = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separator="",
        )

        chunks = []
        for text, metadata in zip(texts, metadatas):
            splits = splitter.split_text(text)
            for i, split in enumerate(splits):
                chunks.append({
                    "chunk_text": split,
                    "metadata": {**metadata, "chunk_index": i},
                })
        return chunks

    @staticmethod
    def _sentence_split(texts, metadatas, chunk_size, chunk_overlap):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[". ", "! ", "? ", "\n"],
        )

        chunks = []
        for text, metadata in zip(texts, metadatas):
            splits = splitter.split_text(text)
            for i, split in enumerate(splits):
                chunks.append({
                    "chunk_text": split,
                    "metadata": {**metadata, "chunk_index": i},
                })
        return chunks

    @staticmethod
    def _markdown_split(texts, metadatas):
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ]

        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

        chunks = []
        for text, metadata in zip(texts, metadatas):
            splits = splitter.split_text(text)
            for i, split in enumerate(splits):
                chunks.append({
                    "chunk_text": split.page_content,
                    "metadata": {**metadata, **split.metadata, "chunk_index": i},
                })
        return chunks
