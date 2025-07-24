import React, { useState } from 'react';
import UserInterface from './components/UserInterface';
import AdminInterface from './components/AdminInterface';

function App() {
  const [currentPage, setCurrentPage] = useState('user');

  return (
    <div>
      {/* 导航栏 */}
      <nav className="bg-gray-800 text-white p-4">
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-bold">论文接受率预测器</h1>
          <div className="space-x-4">
            <button
              onClick={() => setCurrentPage('user')}
              className={`px-4 py-2 rounded ${currentPage === 'user' ? 'bg-blue-600' : 'bg-gray-600'}`}
            >
              用户界面
            </button>
            <button
              onClick={() => setCurrentPage('admin')}
              className={`px-4 py-2 rounded ${currentPage === 'admin' ? 'bg-blue-600' : 'bg-gray-600'}`}
            >
              管理后台
            </button>
          </div>
        </div>
      </nav>

      {/* 页面内容 */}
      {currentPage === 'user' ? <UserInterface /> : <AdminInterface />}
    </div>
  );
}

export default App;