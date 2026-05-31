import chromadb
import os

from ollama import embeddings

class ChromaDB:
    def __init__(self):
        chroma_client = chromadb.CloudClient(
        api_key=os.getenv('CHROMA_API_KEY'),
        tenant=os.getenv('CHROMA_TENANT'),
        database=os.getenv('CHROMA_DATABASE')
        )
        
        self.client = chroma_client

    def add_embeddings(self, collection_name, embeddings, metadatas, documents=None, ids=None):

        collection = self.client.get_or_create_collection(collection_name)
        
        collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids or [f"{collection_name}-{i}" for i in range(len(embeddings))],
            **({"documents": documents} if documents else {})
        ) 
    def retrieve(self, collection_name, query, n_results=5):
        collection = self.client.get_collection(collection_name)
        
        results = collection.query(
            query_texts=query,
            n_results=n_results
        )
        
        return results