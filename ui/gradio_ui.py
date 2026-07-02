import uuid
import gradio as gr
from agents.supervisor import run_supervisor
from auth.auth import authenticate, guest_login

_sessions = {}

def _get_session(sid):
    if sid not in _sessions:
        _sessions[sid] = {"token": "", "session_id": sid, "role": "guest", "display_name": "Guest", "user_id": None, "student_id": None}
    return _sessions[sid]

def _format_debug(r, role):
    dp = "**Role**: {} | **Calls**: {}\n\n".format(role, r.get("iteration_count", 0))
    think_chain = r.get("think_chain", [])
    if think_chain:
        dp += "---\n### Supervisor's Thinking\n\n"
        for tc in think_chain:
            it = tc.get("iteration", 0)
            think_text = tc.get("think", "(no reasoning)")
            decision = tc.get("decision", "?")
            dp += "**Round {}**\n> {}\n\n".format(it, think_text)
            dp += ">>> **DECISION**: `{}`\n\n".format(decision)
    wr = r.get("worker_results", [])
    if wr:
        dp += "---\n### Worker Results\n\n"
        for w in wr:
            ic = "OK" if w.get("status") == "success" else "ERR"
            dp += "{} **{}** ({}ms)\n".format(ic, w.get("worker", "?"), w.get("elapsed_ms", "?"))
    return dp


def respond(msg, history, sid, debug):
    if not msg.strip():
        return history, sid, "", ""
    s = _get_session(sid)
    r = run_supervisor(msg, s["session_id"], s["role"], s["user_id"], s["display_name"], debug, s.get("student_id"))
    reply = r["response"]
    dp = _format_debug(r, s["role"]) if debug else ""
    history = history or []
    history.append({"role": "user", "content": msg})
    history.append({"role": "assistant", "content": reply})
    return history, sid, "", dp


def respond_stream(msg, history, sid, debug):
    if not msg.strip():
        yield history, sid, "", ""
        return
    s = _get_session(sid)
    history = history or []
    history.append({"role": "user", "content": msg})
    history.append({"role": "assistant", "content": "**Supervisor is thinking...**"})
    dp1 = "**Supervisor thinking...**" if debug else ""
    yield history, sid, "", dp1

    r = run_supervisor(msg, s["session_id"], s["role"], s["user_id"], s["display_name"], True, s.get("student_id"))

    think_chain = r.get("think_chain", [])
    if think_chain:
        lines = ["**Supervisor Reasoning:**\n"]
        for tc in think_chain:
            it = tc.get("iteration", 0)
            think_text = tc.get("think", "")
            decision = tc.get("decision", "?")
            lines.append("> **Round {}**: {}".format(it, think_text))
            lines.append("> Decision: `{}`".format(decision))
        lines.append("\n**Executing workers...**")
        history[-1]["content"] = "\n".join(lines)
        yield history, sid, "", "**Executing workers...**" if debug else ""

    worker_results = r.get("worker_results", [])
    if worker_results:
        wr_lines = [history[-1]["content"]] if history else []
        wr_lines.append("\n**Collecting results, generating response...**")
        history[-1]["content"] = "\n".join(wr_lines)
        yield history, sid, "", _format_debug(r, s["role"]) if debug else ""

    reply = r["response"]
    history[-1]["content"] = reply
    dp_final = _format_debug(r, s["role"]) if debug else ""
    yield history, sid, "", dp_final


def clear_chat(sid):
    s = _get_session(sid)
    s["session_id"] = str(uuid.uuid4())[:8]
    return [], sid, "", ""

def try_login(u, p, sid):
    if not u.strip():
        return sid, "Enter username", gr.update(visible=True), gr.update(visible=False)
    sess = authenticate(u, p)
    if sess:
        s = _get_session(sid)
        s["token"] = sess.token
        s["role"] = sess.role
        s["display_name"] = sess.display_name
        s["user_id"] = sess.student_id or sess.username
        s["student_id"] = sess.student_id
        return sid, "OK: {} ({})".format(sess.display_name, sess.role), gr.update(visible=False), gr.update(visible=True)
    return sid, "Login failed", gr.update(visible=True), gr.update(visible=False)

def try_guest_login(sid):
    sess = guest_login()
    s = _get_session(sid)
    s["token"] = sess.token
    s["role"] = "guest"
    s["display_name"] = "Guest"
    s["user_id"] = None
    s["student_id"] = None
    return sid, "Guest mode", gr.update(visible=False), gr.update(visible=True)

def do_logout(sid):
    s = _get_session(sid)
    s["token"] = ""
    s["role"] = "guest"
    s["display_name"] = "Guest"
    s["user_id"] = None
    s["student_id"] = None
    s["session_id"] = str(uuid.uuid4())[:8]
    return sid, [], "", "", gr.update(visible=True), gr.update(visible=False)

def pick_handler(msg, history, sid, debug, stream):
    if stream:
        for result in respond_stream(msg, history, sid, debug):
            yield result
    else:
        result = respond(msg, history, sid, debug)
        yield result

def create_ui():
    with gr.Blocks(title="Smart Campus AI") as demo:
        sid = gr.Textbox(value=str(uuid.uuid4())[:8], visible=False, label="")
        gr.Markdown("# Smart Campus AI Agent")
        gr.Markdown("### Supervisor + Worker Multi-Agent | RBAC | Streaming Reasoning")

        with gr.Column(visible=True) as lc:
            gr.Markdown("### Login")
            gr.Markdown("Test: `admin/admin123` | `teacher_wang/teacher123` | `student_zhang/student123` | Guest")
            with gr.Row():
                ui = gr.Textbox(label="Username", placeholder="admin")
                pi = gr.Textbox(label="Password", type="password", placeholder="admin123")
            with gr.Row():
                lb = gr.Button("Login", variant="primary")
                gb = gr.Button("Guest", variant="secondary")
            lm = gr.Markdown("")

        with gr.Column(visible=False) as mc:
            with gr.Row():
                ui2 = gr.Markdown("**User**: Guest")
                lo = gr.Button("Logout", size="sm")
            with gr.Row():
                with gr.Column(scale=3):
                    cb = gr.Chatbot(label="Chat", height=450)
                    with gr.Row():
                        mi = gr.Textbox(placeholder="Ask anything...", scale=9, show_label=False)
                        sb = gr.Button("Send", variant="primary", scale=1)
                    with gr.Row():
                        cl = gr.Button("New Chat", size="sm")
                        dt = gr.Checkbox(label="Debug", value=False)
                        st_toggle = gr.Checkbox(label="Stream", value=True)
                with gr.Column(scale=1, visible=False) as dc:
                    do = gr.Markdown("Debug trace", elem_id="debug-panel")

        lb.click(try_login, [ui, pi, sid], [sid, lm, lc, mc]).then(
            lambda sid: '**User**: {} ({})'.format(_get_session(sid)["display_name"], _get_session(sid)["role"]), [sid], [ui2])
        gb.click(try_guest_login, [sid], [sid, lm, lc, mc])
        pi.submit(try_login, [ui, pi, sid], [sid, lm, lc, mc]).then(
            lambda sid: '**User**: {} ({})'.format(_get_session(sid)["display_name"], _get_session(sid)["role"]), [sid], [ui2])
        lo.click(do_logout, [sid], [sid, cb, mi, do, lc, mc])
        dt.change(lambda v: gr.Column(visible=v), [dt], [dc])

        sb.click(pick_handler, [mi, cb, sid, dt, st_toggle], [cb, sid, mi, do])
        mi.submit(pick_handler, [mi, cb, sid, dt, st_toggle], [cb, sid, mi, do])
        cl.click(clear_chat, [sid], [cb, sid, mi, do])

    return demo
