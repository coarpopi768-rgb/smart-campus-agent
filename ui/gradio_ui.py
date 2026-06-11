import random
import gradio as gr
from agents.campus_agent import make_agent

agent = make_agent()

SESSION_ID ="default"

def respond(history,msg):

    if history is None:
        history = []

    res = agent.invoke(
        {
            "messages":[
                ("user",msg)
            ]
        },
        config = {
            "configurable": {
                "thread_id": SESSION_ID
            }
        }
    )
    reply = res["messages"][-1].content

    history.append({
        "role":"user",
        "content":msg
    })

    history.append({
        "role":"assistant",
        "content":reply
    })
    return history,""

def clear_fn():
    global SESSION_ID
    SESSION_ID = str(random.random())
    return [],""
def create_ui():
    with gr.Blocks()as demo:

        gr.Markdown(
            "🏫 智慧校园 AI Agent"
        )
        chatbot = gr.Chatbot()

        txt = gr.Textbox(   
            placeholder = "请输入问题"
        )
        btn = gr.Button("清空")

        txt.submit(
            fn = respond,
            inputs = [chatbot,txt],
            outputs = [chatbot,txt]
        )
        btn.click(
            fn = clear_fn,
            outputs = [chatbot,txt]
        )
    return demo