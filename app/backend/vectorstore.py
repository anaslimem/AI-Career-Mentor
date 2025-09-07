from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def build_vector_store(chunks: list) -> Chroma:

    # Base embeddings
    base_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Build vector store with Chroma using cached embeddings
    vector_store = Chroma.from_texts(
    texts=chunks,
    embedding=base_embeddings,
    collection_name="job_descriptions",
    persist_directory="./chroma_db"  # Local folder for persistence
    )
    vector_store.persist()

    return vector_store

def top_k(vector_store: Chroma, query: str, k: int = 5) -> list:
    # Query the vector store
    return vector_store.similarity_search(query, k=k)
