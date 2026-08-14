import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, guestLogin, updateSession } from '../api';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username.trim()) { setError('请输入用户名'); return; }
    setLoading(true);
    setError('');
    try {
      const data = await login(username, password);
      const sid = crypto.randomUUID().slice(0, 8);
      await updateSession(sid, data.token);
      sessionStorage.setItem('session_id', sid);
      sessionStorage.setItem('user', JSON.stringify(data));
      navigate('/chat');
    } catch {
      setError('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await guestLogin();
      const sid = crypto.randomUUID().slice(0, 8);
      await updateSession(sid, data.token);
      sessionStorage.setItem('session_id', sid);
      sessionStorage.setItem('user', JSON.stringify(data));
      navigate('/chat');
    } catch {
      setError('游客登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Smart Campus AI</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Supervisor + Worker Multi-Agent</p>
        </div>
        <form onSubmit={handleLogin} className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 space-y-4">
          <input
            type="text"
            placeholder="用户名"
            value={username}
            onChange={e => setUsername(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          />
          <input
            type="password"
            placeholder="密码"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          />
          {error && <div className="text-red-500 text-xs text-center">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-xl transition text-sm"
          >
            {loading ? '登录中...' : '登录'}
          </button>
          <div className="relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200 dark:border-gray-700"></div></div>
            <div className="relative flex justify-center text-xs"><span className="bg-white dark:bg-gray-800 px-2 text-gray-400">或</span></div>
          </div>
          <button
            type="button"
            onClick={handleGuest}
            disabled={loading}
            className="w-full py-3 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 font-medium rounded-xl transition text-sm"
          >
            游客登录
          </button>
          <div className="text-xs text-gray-400 text-center mt-4">
            测试账号: admin/admin123 · teacher_wang/teacher123 · student_zhang/student123
          </div>
        </form>
      </div>
    </div>
  );
}
