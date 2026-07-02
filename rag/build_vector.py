"""
??????? ?? ? knowledge.txt ?? FAISS ??
??: python rag/build_vector.py
"""
import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ??
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "knowledge.txt")
VECTOR_DIR = os.path.join(BASE_DIR, "vectorstore")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# ????
loader = TextLoader(KNOWLEDGE_FILE, encoding="utf-8")
docs = loader.load()
print(f"[OK] Loaded {len(docs)} document(s)")

# ??
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "?", "?", "?", "?", "?", " ", ""]
)
chunks = splitter.split_documents(docs)
print(f"[OK] Split into {len(chunks)} chunks")

# ???
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"}
)

db = FAISS.from_documents(chunks, embeddings)

# ??
os.makedirs(VECTOR_DIR, exist_ok=True)
db.save_local(VECTOR_DIR)
print(f"[DONE] Vector database saved to {VECTOR_DIR}")
