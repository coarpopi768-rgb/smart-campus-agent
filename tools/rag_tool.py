from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"}
)

db = FAISS.load_local(
    "rag/vectorstore",
    embeddings, 
    allow_dangerous_deserialization=True
)

@tool
def school_rag_query(query:str):
    """校园知识库查询，用于查询校园制度、课程、通知等
    参数：
        query: 要查询的关键词
    """
    docs = db.similarity_search(
        query,
        k=3
    )
    result = []

    for doc in docs:
        result.append(doc.page_content)
    return "\n".join(result)


