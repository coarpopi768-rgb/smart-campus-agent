import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatMessage from '../components/ChatMessage';
import DebugPanel from '../components/DebugPanel';
import { streamChat, sendChat } from '../api';

export default function ChatPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [debug, setDebug] = useState(false);
  const [stream, setStream] = useState(true);
  const [thinkChain, setThinkChain] = useState([]);
  const [workerResults, setWorkerResults] = useState([]);
  const bottomRef = useRef(null);
  const user = JSON.parse(sessionStorage.getItem('user') || '{"display_name":"Guest","role":"guest"}');
  const sid = sessionStorage.getItem('session_id') || '';

  useEffect(() => {
    if (!sid) navigate('/');
  }, [sid, navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);

    if (stream) {
      setLoading(true);
      const reader = streamChat(msg, sid, debug).getReader();
      let accumulated = '';
      let tc = [];
      let wr = [];
      let receivedFinal = false;
      const assistantIdx = messages.length + 1;
      setMessages(prev => [...prev, { role: 'assistant', content: '...' }]);

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          switch (value.type) {
            case 'supervisor_thinking':
              setMessages(prev => {
                const n = [...prev];
                n[assistantIdx] = { role: 'assistant', content: 'Supervisor 正在思考...' };
                return n;
              });
              break;
            case 'supervisor_decided':
              if (value.think_chain) {
                tc = [...tc, ...value.think_chain];
                setThinkChain(tc);
              }
              break;
            case 'worker_start':
              setMessages(prev => {
                const n = [...prev];
                n[assistantIdx] = { role: 'assistant', content: '正在调用 ' + value.worker + '...' };
                return n;
              });
              break;
            case 'worker_done':
              if (value.results) { wr = [...wr, ...value.results]; setWorkerResults(wr); }
              break;
            case 'error':
              // 后端返回 401/500 等错误（见 api.js streamChat）
              receivedFinal = true;
              setMessages(prev => {
                const n = [...prev];
                n[assistantIdx] = { role: 'assistant', content: value.message || '请求失败，请重试' };
                return n;
              });
              break;
            case 'done':
              receivedFinal = true;
              accumulated = value.response;
              setMessages(prev => {
                const n = [...prev];
                n[assistantIdx] = { role: 'assistant', content: accumulated };
                return n;
              });
              if (value.think_chain) setThinkChain(value.think_chain);
              if (value.worker_results) setWorkerResults(value.worker_results);
              break;
          }
        }
        // 流异常中断（没有收到 done/error）时给出提示，避免界面一直停留在 "..."
        if (!receivedFinal) {
          setMessages(prev => {
            const n = [...prev];
            n[assistantIdx] = { role: 'assistant', content: '连接中断，请重试' };
            return n;
          });
        }
      } catch {
        setMessages(prev => {
          const n = [...prev];
          n[assistantIdx] = { role: 'assistant', content: '请求失败，请重试' };
          return n;
        });
      }
      setLoading(false);
    } else {
      setLoading(true);
      try {
        const data = await sendChat(msg, sid, debug);
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
        if (debug) {
          setThinkChain(data.think_chain || []);
          setWorkerResults(data.worker_results || []);
        }
      } catch {
        setMessages(prev => [...prev, { role: 'assistant', content: '请求失败，请重试' }]);
      }
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    const newSid = crypto.randomUUID().slice(0, 8);
    sessionStorage.setItem('session_id', newSid);
    setMessages([]);
    setThinkChain([]);
    setWorkerResults([]);
  };

  const handleLogout = () => {
    sessionStorage.clear();
    navigate('/');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-gray-950">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-gray-900 dark:text-white">Smart Campus AI</h1>
          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300">
            {user.role}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">{user.display_name}</span>
          <button onClick={handleLogout} className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition">
            退出
          </button>
        </div>
      </header>

      {/* Main */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-600 text-sm">
                开始对话吧 🎓
              </div>
            )}
            {messages.map((m, i) => <ChatMessage key={i} msg={m} />)}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 dark:border-gray-800 p-4">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息，Enter 发送..."
                rows={1}
                className="flex-1 resize-none rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-4 py-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-xl transition"
              >
                {loading ? '...' : '发送'}
              </button>
            </div>
            <div className="flex items-center gap-4 mt-2">
              <button onClick={handleNewChat} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition">新建会话</button>
              <label className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer">
                <input type="checkbox" checked={debug} onChange={e => setDebug(e.target.checked)} className="rounded" />
                Debug
              </label>
              <label className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer">
                <input type="checkbox" checked={stream} onChange={e => setStream(e.target.checked)} className="rounded" />
                流式
              </label>
            </div>
          </div>
        </div>

        {/* Debug Panel */}
        <DebugPanel thinkChain={thinkChain} workerResults={workerResults} visible={debug} />
      </div>
    </div>
  );
}
