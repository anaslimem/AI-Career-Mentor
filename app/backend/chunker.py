from chonkie import TokenChunker

def chunk_text(text: str):
    chunker = TokenChunker(chunk_size=800, chunk_overlap=120)
    return [c.text for c in chunker(text)]
