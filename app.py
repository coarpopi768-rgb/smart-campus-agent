# Smart Campus AI - 启动入口
#
# 新前端（推荐）:
#   uvicorn api.main:app --host 0.0.0.0 --port 8000
#   然后 cd frontend && npm run dev
#
# 旧 Gradio UI（兼容）:
#   python app.py --gradio

import sys

if __name__ == "__main__":
    if "--gradio" in sys.argv:
        from ui.gradio_ui import create_ui
        demo = create_ui()
        demo.launch()
    else:
        import uvicorn
        uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
