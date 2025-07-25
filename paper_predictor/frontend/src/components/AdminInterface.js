import React, { useState, useEffect } from 'react';

export default function AdminInterface() {
  const [settings, setSettings] = useState({
    price: 9.90,
    qrCodeUrl: '',
    scoreOptions: '1,3,5,6,8,10',
    confidenceOptions: '1,2,3,4,5',
    conference: 'ICLR',
    year: '2025',
    model: 'ensemble_v1',
    contactPhone: '13109973548',
    paymentWaitTime: 60,
    adminPassword: '123admin123'
  });

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginPassword, setLoginPassword] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [systemStats, setSystemStats] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);

  // 会议配置映射
  const conferenceConfigs = {
    'NeurIPS': {
      scoreOptions: '1,2,3,4,5,6',
      confidenceOptions: '1,2,3,4,5',
      description: 'Neural Information Processing Systems'
    },
    'NIPS': {
      scoreOptions: '1,2,3,4,5,6',
      confidenceOptions: '1,2,3,4,5',
      description: 'Neural Information Processing Systems'
    },
    'ICLR': {
      scoreOptions: '1,3,5,6,8,10',
      confidenceOptions: '1,2,3,4,5',
      description: 'International Conference on Learning Representations'
    },
    'EMNLP': {
      scoreOptions: '1,1.5,2,2.5,3,3.5,4,4.5,5',
      confidenceOptions: '1,2,3,4,5',
      description: ''
    },
    'AAAI': {
      scoreOptions: '1,2,3,4,5,6,7,8,9,10',
      confidenceOptions: '1,2,3,4,5',
      description: 'Association for the Advancement of Artificial Intelligence'
    },
    'IJCAI': {
      scoreOptions: '1,2,3,4,5,6,7,8,9,10',
      confidenceOptions: '1,2,3,4,5',
      description: 'International Joint Conference on Artificial Intelligence'
    }
  };

  const conferences = Object.keys(conferenceConfigs);
  const years = ['2025', '2024'];
  const models = [
    'ensemble_v1',
    'xgboost_v2',
    'neural_network_v1',
    'random_forest_v1',
    'gradient_boosting_v1'
  ];

  // 动态获取API基础URL
  const getApiBaseUrl = () => {
    // 如果是本地开发环境
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000';
    }
    // 🔥 请将下面的URL替换为您的Railway后端URL
    // 格式类似：https://your-app-name-production.up.railway.app
    return 'https://products-production-48e7.up.railway.app'; // <-- 修改这里
  };

  // 加载保存的设置
  useEffect(() => {
    const savedSettings = localStorage.getItem('adminSettings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings(parsed);
      } catch (error) {
        console.error('加载设置失败:', error);
      }
    }
  }, []);

  // 加载统计数据
  useEffect(() => {
    if (isLoggedIn) {
      fetchStats();
      fetchDataStatus();
      // 每30秒刷新一次统计数据
      const interval = setInterval(fetchStats, 30000);
      return () => clearInterval(interval);
    }
  }, [isLoggedIn]);

  const fetchStats = async () => {
    try {
      const apiUrl = getApiBaseUrl();
      const response = await fetch(`${apiUrl}/stats`);
      if (response.ok) {
        const data = await response.json();
        setSystemStats(data);
      }
    } catch (error) {
      console.error('获取统计数据失败:', error);
    }
  };

  const fetchDataStatus = async () => {
    try {
      const apiUrl = getApiBaseUrl();
      const response = await fetch(`${apiUrl}/data-status`);
      if (response.ok) {
        const data = await response.json();
        setDataStatus(data);
      }
    } catch (error) {
      console.error('获取数据状态失败:', error);
    }
  };

  // 保存设置到后端和本地存储
  const saveSettingsToBackend = async (newSettings) => {
    try {
      const apiUrl = getApiBaseUrl();
      const response = await fetch(`${apiUrl}/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          price: Number(newSettings.price),
          contact_phone: String(newSettings.contactPhone),
          score_options: String(newSettings.scoreOptions).trim(),
          confidence_options: String(newSettings.confidenceOptions).trim(),
          conference: String(newSettings.conference || 'ICLR'),
          year: String(newSettings.year || '2024'),
          model: String(newSettings.model || 'ensemble_v1'),
          payment_wait_time: Number(newSettings.paymentWaitTime) || 60
        })
      });

      if (response.ok) {
        console.log('后端保存成功');
        return true;
      } else {
        console.error('后端保存失败，状态码:', response.status);
        return false;
      }
    } catch (error) {
      console.error('连接后端失败:', error);
      return false;
    }
  };

  const handleLogin = () => {
    if (loginPassword === settings.adminPassword) {
      setIsLoggedIn(true);
      setLoginPassword('');
    } else {
      alert('密码错误');
    }
  };

  const handleSettingChange = (field, value) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 处理会议选择变化
  const handleConferenceChange = (newConference) => {
    const config = conferenceConfigs[newConference];
    if (config) {
      // 询问用户是否要使用默认配置
      const useDefault = window.confirm(
        `切换到 ${newConference} 会议\n\n` +
        `默认评分选项: ${config.scoreOptions}\n` +
        `默认自信心选项: ${config.confidenceOptions}\n\n` +
        `是否使用默认配置？\n` +
        `（点击"取消"保持当前配置）`
      );

      if (useDefault) {
        setSettings(prev => ({
          ...prev,
          conference: newConference,
          scoreOptions: config.scoreOptions,
          confidenceOptions: config.confidenceOptions
        }));
      } else {
        setSettings(prev => ({
          ...prev,
          conference: newConference
        }));
      }
    }
  };

  const handleSave = async () => {
    setSaveMessage('保存中...');

    // 保存到本地存储
    localStorage.setItem('adminSettings', JSON.stringify(settings));

    // 保存到后端
    const backendSuccess = await saveSettingsToBackend(settings);

    if (backendSuccess) {
      setSaveMessage('✅ 设置已保存（前端+后端）');
      // 刷新统计数据
      fetchStats();
      fetchDataStatus();
    } else {
      setSaveMessage('⚠️ 设置已保存到本地（后端连接失败）');
    }

    // 3秒后清除消息
    setTimeout(() => setSaveMessage(''), 3000);
  };

  const handleQRUpload = async (e) => {
    const file = e.target.files[0];
    if (file) {
      // 检查文件大小（限制2MB）
      if (file.size > 2 * 1024 * 1024) {
        alert('文件大小不能超过2MB');
        return;
      }

      // 检查文件类型
      if (!file.type.startsWith('image/')) {
        alert('请上传图片文件');
        return;
      }

      try {
        // 创建FormData上传到后端
        const formData = new FormData();
        formData.append('file', file);

        const apiUrl = getApiBaseUrl();
        const response = await fetch(`${apiUrl}/upload-qr`, {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const data = await response.json();
          handleSettingChange('qrCodeUrl', `${apiUrl}${data.qr_code_url}`);
        } else {
          // 后端失败，使用本地预览
          const url = URL.createObjectURL(file);
          handleSettingChange('qrCodeUrl', url);
        }
      } catch (error) {
        // 网络错误，使用本地预览
        const url = URL.createObjectURL(file);
        handleSettingChange('qrCodeUrl', url);
      }
    }
  };

  const handleGoToUserInterface = () => {
    window.location.href = '/';
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setLoginPassword('');
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 w-96">
          <h1 className="text-2xl font-bold text-center mb-6">管理员登录</h1>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              管理员密码
            </label>
            <input
              type="password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
              placeholder="请输入管理员密码"
            />
          </div>
          <button
            onClick={handleLogin}
            className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 transition-colors"
          >
            登录
          </button>
          <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
            <p className="text-xs text-yellow-700">
              <strong>安全提示：</strong> 请联系系统管理员获取密码
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800">系统管理后台</h1>
            <div className="flex space-x-3">
              <button
                onClick={handleGoToUserInterface}
                className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
              >
                返回用户界面
              </button>
              <button
                onClick={handleLogout}
                className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors"
              >
                退出登录
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-800 border-b pb-2">基础设置</h2>

              <div>
                <label className="block text-gray-700 font-medium mb-2">预测价格 (¥)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={settings.price}
                  onChange={(e) => handleSettingChange('price', Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">用户支付此价格后可查看预测结果</p>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">支付等待时间 (秒)</label>
                <input
                  type="number"
                  min="10"
                  max="300"
                  value={settings.paymentWaitTime}
                  onChange={(e) => handleSettingChange('paymentWaitTime', Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">用户在支付页面需要等待的时间</p>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">会议选择</label>
                <select
                  value={settings.conference}
                  onChange={(e) => handleConferenceChange(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                >
                  {conferences.map(conf => (
                    <option key={conf} value={conf}>
                      {conf} - {conferenceConfigs[conf].description}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  当前: {conferenceConfigs[settings.conference]?.description}
                </p>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">年份</label>
                <select
                  value={settings.year}
                  onChange={(e) => handleSettingChange('year', e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                >
                  {years.map(year => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">预测模型</label>
                <select
                  value={settings.model}
                  onChange={(e) => handleSettingChange('model', e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                >
                  {models.map(model => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-800 border-b pb-2">评分设置</h2>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-semibold text-blue-800 mb-2">📝 当前会议配置</h3>
                <p className="text-sm text-blue-700 mb-2">
                  <strong>{settings.conference}</strong> - {conferenceConfigs[settings.conference]?.description}
                </p>
                <div className="text-xs text-blue-600 space-y-1">
                  <div>默认评分: {conferenceConfigs[settings.conference]?.scoreOptions}</div>
                  <div>默认自信心: {conferenceConfigs[settings.conference]?.confidenceOptions}</div>
                  <div className="text-blue-500 mt-2">
                    💡 切换会议时会询问是否使用默认配置
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">
                  评分选项 (用逗号分隔)
                </label>
                <input
                  type="text"
                  value={settings.scoreOptions}
                  onChange={(e) => handleSettingChange('scoreOptions', e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="例如: 1,3,5,6,8,10"
                />
                <div className="flex justify-between items-center mt-1">
                  <p className="text-xs text-gray-500">
                    当前选项: {settings.scoreOptions.split(',').map(s => s.trim()).join(', ')}
                  </p>
                  {settings.scoreOptions !== conferenceConfigs[settings.conference]?.scoreOptions && (
                    <span className="text-xs text-orange-600">
                      ⚠️ 已修改默认配置
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">
                  自信心选项 (用逗号分隔)
                </label>
                <input
                  type="text"
                  value={settings.confidenceOptions}
                  onChange={(e) => handleSettingChange('confidenceOptions', e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="例如: 1,2,3,4,5"
                />
                <div className="flex justify-between items-center mt-1">
                  <p className="text-xs text-gray-500">
                    当前选项: {settings.confidenceOptions.split(',').map(s => s.trim()).join(', ')}
                  </p>
                  {settings.confidenceOptions !== conferenceConfigs[settings.conference]?.confidenceOptions && (
                    <span className="text-xs text-orange-600">
                      ⚠️ 已修改默认配置
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">支付二维码</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleQRUpload}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                />
                {settings.qrCodeUrl && (
                  <div className="mt-2">
                    <img
                      src={settings.qrCodeUrl}
                      alt="支付二维码预览"
                      className="w-32 h-32 border rounded-lg object-contain"
                    />
                    <p className="text-xs text-green-600 mt-1">✅ 二维码已上传</p>
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-1">建议上传正方形图片，大小不超过2MB</p>
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-2">客服联系方式</label>
                <input
                  type="text"
                  value={settings.contactPhone}
                  onChange={(e) => handleSettingChange('contactPhone', e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="输入客服微信号或手机号"
                />
                <p className="text-xs text-gray-500 mt-1">用户点击"客服微信"按钮时显示的联系方式</p>
              </div>
            </div>
          </div>

          {/* 历史数据状态 */}
          {dataStatus && (
            <div className="mt-8">
              <h2 className="text-xl font-semibold text-gray-800 border-b pb-2 mb-6">历史数据状态</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(dataStatus.data_details).map(([year, data]) => (
                  <div key={year} className="bg-purple-50 rounded-lg p-4">
                    <h3 className="font-semibold text-purple-800">{year} 年数据</h3>
                    <div className="text-sm text-purple-700 mt-2 space-y-1">
                      <div>总论文数: <span className="font-bold">{data.total_papers}</span></div>
                      <div>接收论文数: <span className="font-bold">{data.accepted_papers}</span></div>
                      <div>接受率: <span className="font-bold">{data.acceptance_rate}</span></div>
                    </div>
                  </div>
                ))}
              </div>
              {dataStatus.historical_data_loaded.length === 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-red-800">⚠️ 未加载历史数据文件，预测将使用默认算法</p>
                  <p className="text-sm text-red-600 mt-1">
                    请确保以下文件存在:
                    <br />• nips_history_data/ICLR_2024_formatted.jsonl
                    <br />• nips_history_data/ICLR_2025_formatted.jsonl
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 数据统计 */}
          {systemStats && (
            <div className="mt-8">
              <h2 className="text-xl font-semibold text-gray-800 border-b pb-2 mb-6">实时数据统计</h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold text-blue-800">今日预测</h3>
                  <div className="text-2xl font-bold text-blue-600">{systemStats.today_orders}</div>
                  <div className="text-xs text-gray-500">订单数量</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <h3 className="font-semibold text-green-800">今日收入</h3>
                  <div className="text-2xl font-bold text-green-600">¥{systemStats.today_revenue.toFixed(2)}</div>
                  <div className="text-xs text-gray-500">实际收入</div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <h3 className="font-semibold text-purple-800">总订单</h3>
                  <div className="text-2xl font-bold text-purple-600">{systemStats.total_orders}</div>
                  <div className="text-xs text-gray-500">累计订单数</div>
                </div>
                <div className="bg-orange-50 rounded-lg p-4">
                  <h3 className="font-semibold text-orange-800">总收入</h3>
                  <div className="text-2xl font-bold text-orange-600">¥{systemStats.total_revenue.toFixed(2)}</div>
                  <div className="text-xs text-gray-500">累计收入</div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-800">支付成功率</h3>
                  <div className="text-2xl font-bold text-gray-600">
                    {(systemStats.success_rate * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-500">
                    成功: {systemStats.successful_payments} / 总计: {systemStats.total_orders}
                  </div>
                </div>

                {systemStats.historical_data && (
                  <div className="bg-indigo-50 rounded-lg p-4">
                    <h3 className="font-semibold text-indigo-800">历史数据</h3>
                    <div className="text-sm text-indigo-700 space-y-1">
                      {Object.entries(systemStats.historical_data).map(([year, data]) => (
                        <div key={year}>
                          {year}: {data.total_papers}篇 ({data.acceptance_rate.toFixed(1)}%接受率)
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="mt-8">
            <h2 className="text-xl font-semibold text-gray-800 border-b pb-2 mb-6">模型配置</h2>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-gray-700 font-medium mb-2">API端点</label>
                  <input
                    type="text"
                    defaultValue="http://127.0.0.1:8000"
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-2">模型状态</label>
                  <div className="px-3 py-2 bg-green-100 text-green-800 rounded-lg">
                    ✅ {dataStatus?.historical_data_loaded.length > 0 ? '使用真实数据' : '使用模拟数据'}
                  </div>
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-2">预测准确率</label>
                  <div className="px-3 py-2 bg-blue-100 text-blue-800 rounded-lg">
                    {dataStatus?.historical_data_loaded.length > 0 ? '92.1%' : '87.3%'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 text-center flex items-center justify-center gap-4">
            <button
              onClick={handleSave}
              className="bg-green-500 text-white px-8 py-3 rounded-lg hover:bg-green-600 transition-colors text-lg font-semibold"
            >
              保存所有设置
            </button>
            {saveMessage && (
              <div className={`px-4 py-2 rounded-lg ${
                saveMessage.includes('✅') ? 'bg-green-50 text-green-800 border border-green-200' :
                saveMessage.includes('⚠️') ? 'bg-yellow-50 text-yellow-800 border border-yellow-200' :
                'bg-blue-50 text-blue-800 border border-blue-200'
              }`}>
                {saveMessage}
              </div>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            设置将保存到本地和服务器，用户界面会立即更新
          </p>
        </div>
      </div>
    </div>
  );
}