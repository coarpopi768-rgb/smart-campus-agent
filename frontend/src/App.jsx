import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import LoginPage from './pages/Login';
import ChatPage from './pages/Chat';

export default function App() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  return (
    <div className={dark ? 'dark' : ''}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </BrowserRouter>
      <button
        onClick={() => setDark(!dark)}
        className="fixed bottom-4 right-4 w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center shadow-lg hover:scale-110 transition text-lg z-50"
        title="切换主题"
      >
        {dark ? '☀️' : '🌙'}
      </button>
    </div>
  );
}
