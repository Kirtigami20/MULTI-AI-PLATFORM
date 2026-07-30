RAG_CONTEXT_HEADER = "Relevant context from knowledge base:"
RAG_NO_RESULTS = "No relevant context found in the knowledge base."


def format_rag_context(chunks: list[dict]) -> str:
    if not chunks:
        return RAG_NO_RESULTS

    parts = [RAG_CONTEXT_HEADER, ""]

    for i, chunk in enumerate(chunks, 1):
        score = chunk.get("score", 0)
        source = chunk.get("metadata", {}).get("source", "unknown")
        text = chunk.get("chunk_text", "")
        parts.append(f"[{i}] (source: {source}, relevance: {score:.2f})")
        parts.append(text)
        parts.append("")

    return "\n".join(parts)


def build_rag_augmented_query(query: str, rag_context: str) -> str:
    if rag_context == RAG_NO_RESULTS:
        return query

    return (
        f"{rag_context}\n\n"
        f"---\n\n"
        f"User question: {query}\n\n"
        f"Answer based on the context above when relevant. "
        f"If the context does not contain the answer, say so clearly."
    )
