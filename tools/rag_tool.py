"""
校园知识库 RAG 检索工具
"""
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from config.settings import RAG_EMBEDDING_MODEL, RAG_VECTORSTORE_PATH, RAG_RETRIEVAL_K

# 延迟加载向量数据库
_vectordb = None

def _get_vectordb():
    global _vectordb
    if _vectordb is None:
        embeddings = HuggingFaceEmbeddings(
            model_name=RAG_EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"}
        )
        _vectordb = FAISS.load_local(
            RAG_VECTORSTORE_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
    return _vectordb


@tool
def school_rag_query(query: str) -> str:
    """
    校园知识库检索工具。用于查询校园制度、课程安排、通知公告、办事流程等。
    
    参数:
        query: 要检索的关键词或问题，如"请假流程"、"食堂开放时间"、"奖学金申请"
    
    返回:
        检索到的相关知识片段
    """
    if not query.strip():
        return "[错误] 查询内容不能为空。"
    
    try:
        db = _get_vectordb()
        docs = db.similarity_search(query, k=RAG_RETRIEVAL_K)
        
        if not docs:
            return "[检索结果为空] 知识库中未找到与您问题相关的内容。建议您联系教务处或辅导员获取最新信息。"
        
        # 格式化结果
        results = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content.strip()
            if content:
                results.append(f"【来源 {i}】\n{content}")
        
        if not results:
            return "[检索结果为空] 未找到有效内容。"
        
        return "\n\n".join(results)
    
    except Exception as e:
        return f"[错误] 知识库检索异常: {str(e)}"
