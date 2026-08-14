const BASE = '/api';

export async function login(username, password) {
  const res = await fetch(BASE + '/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error('Login failed');
  return res.json();
}

export async function guestLogin() {
  const res = await fetch(BASE + '/auth/guest', { method: 'POST' });
  if (!res.ok) throw new Error('Guest login failed');
  return res.json();
}

export async function sendChat(message, sessionId, debug = false) {
  const res = await fetch(BASE + '/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, debug }),
  });
  if (!res.ok) throw new Error('Chat failed');
  return res.json();
}

export function streamChat(message, sessionId, debug = false) {
  const params = new URLSearchParams({ message, session_id: sessionId, debug });
  return new ReadableStream({
    async start(controller) {
      const res = await fetch(BASE + '/chat/stream?' + params);
      // 后端返回 401/500 等错误时，把错误信息传给 UI，避免界面永远卡在 "..."
      if (!res.ok) {
        let detail = '请求失败 (' + res.status + ')';
        try { const err = await res.json(); if (err.detail) detail = err.detail; } catch {}
        controller.enqueue({ type: 'error', message: detail });
        controller.close();
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        // 服务端异常中断时也要正常结束流，否则前端 read() 永远不返回
        if (done) { controller.close(); return; }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') { controller.close(); return; }
            try { controller.enqueue(JSON.parse(data)); } catch {}
          }
        }
      }
    }
  });
}

export async function updateSession(sessionId, token) {
  // 角色/身份由服务端从 token 会话派生，前端只提交 token，防止提权
  await fetch(BASE + '/session/update?' + new URLSearchParams({
    session_id: sessionId,
    token,
  }), { method: 'POST' });
}
