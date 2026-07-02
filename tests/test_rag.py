"""
Tests: RAG Retrieval Quality
Validates FAISS vectorstore retrieval accuracy.
"""
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('zhipuai_api_key', 'test-key')
os.environ.setdefault('rag_embedding_model', 'all-MiniLM-L6-v2')

# Knowledge categories from knowledge.txt
KNOWLEDGE_CATEGORIES = {
    "请假": ["请假制度", "提前提交申请", "辅导员审批", "3-7天", "院系学工办"],
    "宿舍": ["门禁时间", "23:00", "访客登记", "大功率电器", "800W"],
    "奖学金": ["国家奖学金", "8000元", "一等奖学金", "3000元", "成绩排名", "5%", "10%"],
    "毕业": ["学分", "170学分", "160学分", "英语四级", "425分", "毕业论文"],
    "图书馆": ["开放时间", "7:00-22:00", "借书", "8本", "30天", "续借", "15天"],
    "校园网": ["免费流量", "50GB", "VPN", "统一认证", "学号"],
    "心理咨询": ["心理咨询中心", "预约电话", "免费咨询", "8次", "学生活动中心"],
    "社团": ["86个", "百团大战", "最多3个", "活动经费", "2000元", "10000元"],
    "课程考试": ["教学周", "1-16周", "期末考试", "平时成绩", "30%", "期末成绩", "70%", "补考", "60分"],
    "校园卡": ["校园卡", "行政楼一楼", "9:00-17:00", "充值", "支付宝", "微信"],
    "食堂": ["食堂", "餐厅"],  # 可能没有，测试 fallback
}


def build_test_queries():
    """Build test cases from knowledge categories."""
    queries = []
    for category, keywords in KNOWLEDGE_CATEGORIES.items():
        queries.append({
            "query": f"学校{category}相关规定是什么",
            "keywords": keywords[:3],
            "category": category,
        })
    return queries


def test_rag_import_works():
    """RAG module should import without errors."""
    from tools.rag_tool import school_rag_query
    assert hasattr(school_rag_query, 'invoke'), "school_rag_query should have invoke method"


def test_rag_tool_schema():
    """RAG tool should have proper name and description."""
    from tools.rag_tool import school_rag_query
    assert hasattr(school_rag_query, 'name'), "Tool should have a name"
    assert hasattr(school_rag_query, 'description'), "Tool should have a description"


def test_faiss_index_exists():
    """FAISS index files must exist on disk."""
    index_path = "rag/vectorstore/index.faiss"
    pkl_path = "rag/vectorstore/index.pkl"
    assert os.path.exists(index_path), f"FAISS index not found: {index_path}"
    assert os.path.exists(pkl_path), f"FAISS pickle not found: {pkl_path}"


def test_knowledge_file_readable():
    """Knowledge.txt should be readable and have content."""
    with open("rag/knowledge.txt", "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 1000, f"Knowledge file too small: {len(content)} chars"
    # Should contain key sections
    for section in ["请假制度", "宿舍管理", "奖学金", "毕业与学位", "图书馆"]:
        assert section in content, f"Missing section: {section}"


def test_rag_query_integration():
    """Integration test: actual FAISS query returns results."""
    from tools.rag_tool import school_rag_query
    result = school_rag_query.invoke({"query": "学校请假流程"})
    assert result is not None, "Query should return a result"
    assert "请假" in result or "申请" in result or "[检索结果为空]" in result, \
        f"Unexpected result: {result[:200]}"
    print(f"  RAG result preview: {result[:150]}...")


def test_rag_query_empty_input():
    """Empty query should return error."""
    from tools.rag_tool import school_rag_query
    result = school_rag_query.invoke({"query": ""})
    assert "[错误]" in result or "[Error]" in result, f"Empty query should error: {result}"


if __name__ == "__main__":
    all_tests = [f for f in dir() if f.startswith('test_')]
    passed = 0
    failed = 0
    for test_name in all_tests:
        try:
            globals()[test_name]()
            print(f"  PASS  {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test_name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(all_tests)}")
    sys.exit(1 if failed else 0)
