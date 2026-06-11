from langchain.agents import create_agent
from langchain_community.chat_models import ChatZhipuAI
from config.settings import *
from config.prompt import SYS_PROMPT

from tools.rag_tool import school_rag_query
from tools.student_tool import student_query
from tools.score_tool import score_query
from tools.email_tool import send_email
from tools.baidu_tool import baidu_search

def make_agent():

    llm = ChatZhipuAI(
        model = "glm-4-plus",
        api_key = ZHIPUAI_API_KEY,
        temperature = 0.1,
        timeout = 120
    )

    tools = [
        student_query,
        score_query,
        send_email,
        baidu_search,
        school_rag_query
    ]
    system_prompt = """
    你是智慧校园智能助手
    """

    agent = create_agent(
        model = llm,
        tools = tools,
        system_prompt = SYS_PROMPT
    )
    return agent
