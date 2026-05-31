from pathlib import Path
from typing import List
from sentence_transformers import SentenceTransformer

from data.chromadb_da import ChromaDB


class RagHelper:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def chunk_text(self,text: str, 
        chunk_size: int, 
        chunk_overlap: int) -> List[str]:
        sentences = sent_tokenize(text)
        
        chunks = []
        current_chunk = []
        current_len = 0

        for sent in sentences:
            words = sent.split()
            if current_len + len(words) > chunk_size:
                chunks.append(" ".join(current_chunk))

                # overlap
                overlap_words = current_chunk[-chunk_overlap:] if chunk_overlap > 0 else []
                current_chunk = overlap_words + words
                current_len = len(current_chunk)
            else:
                current_chunk.extend(words)
                current_len += len(words)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def save_vector_embeddings(
        self,
        file_path,
        collection_name,
        chunk_size=80,
        chunk_overlap=20,
        base_metadata=None,
    ):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        chunks = self.chunk_text(
            path.read_text(encoding="utf-8", errors="ignore"),
            chunk_size,
            chunk_overlap
        )
        if not chunks:
            return 0

        embeddings = self.model.encode(
            chunks,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True  # good for cosine similarity
        )

        base = base_metadata or {}
        metadatas = [
            {
                "source_file": path.name,
                "source_path": str(path),
                "chunk_index": i,
                "chunk_length": len(chunk),
                **base,
            }
            for i, chunk in enumerate(chunks)
        ]

        ids = [f"{path.stem}-{i}" for i in range(len(chunks))]

        ChromaDB.add_embeddings(
            collection_name,
            embeddings,
            metadatas,
            documents=chunks,
            ids=ids,
        )

        return len(chunks)