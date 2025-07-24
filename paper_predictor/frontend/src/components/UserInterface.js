import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function UserInterface() {
  // 动态评审人数支持
  const [reviewerCount, setReviewerCount] = useState(4);
  const [scores, setScores] = useState({});
  const [confidences, setConfidences] = useState({});

  const [prediction, setPrediction] = useState(null);
  const [showPayment, setShowPayment] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState('pending');
  const [isLoading, setIsLoading] = useState(false);

  // 支付等待倒计时
  const [waitingTime, setWaitingTime] = useState(0);
  const [isWaiting, setIsWaiting] = useState(false);

  // 从后端获取的设置
  const [settings, setSettings] = useState({
    price: 9.90,
    qrCodeUrl: '',
    scoreOptions: [1, 3, 5, 6, 8, 10],
    confidenceOptions: [1, 2, 3, 4, 5],
    contactPhone: '13109973548',
    paymentWaitTime: 60 // 默认60秒等待时间
  });

  // 历史数据统计
  const [historicalStats, setHistoricalStats] = useState({
    totalPapers: 12000,
    acceptedPapers: 3000,
    acceptanceRate: 0.25
  });

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

  // 获取后端设置
  useEffect(() => {
    fetchSettings();
  }, []);

  // 支付等待倒计时效果
  useEffect(() => {
    let timer;
    if (isWaiting && waitingTime > 0) {
      timer = setInterval(() => {
        setWaitingTime(prev => prev - 1);
      }, 1000);
    } else if (waitingTime === 0 && isWaiting) {
      setIsWaiting(false);
    }
    return () => clearInterval(timer);
  }, [isWaiting, waitingTime]);

  const fetchSettings = async () => {
    try {
      const apiUrl = getApiBaseUrl();
      const response = await fetch(`${apiUrl}/settings`);
      if (response.ok) {
        const data = await response.json();

        // 转换后端数据格式 (snake_case -> camelCase)
        const convertedSettings = {
          price: data.price || 9.90,
          qrCodeUrl: data.qr_code_url ? `${apiUrl}${data.qr_code_url}` : '',
          scoreOptions: data.score_options || [1, 3, 5, 6, 8, 10],
          confidenceOptions: data.confidence_options || [1, 2, 3, 4, 5],
          contactPhone: data.contact_phone || '13109973548',
          conference: data.conference || 'NeurIPS',
          year: data.year || '2024',
          model: data.model || 'ensemble_v1',
          paymentWaitTime: data.payment_wait_time || 60
        };

        setSettings(convertedSettings);
      }
    } catch (error) {
      console.log('无法连接后端，使用默认设置');
    }
  };

  // 添加/删除评审人
  const addReviewer = () => {
    if (reviewerCount < 10) { // 最多10个评审
      setReviewerCount(reviewerCount + 1);
    }
  };

  const removeReviewer = () => {
    if (reviewerCount > 1) { // 至少1个评审
      const newCount = reviewerCount - 1;
      setReviewerCount(newCount);

      // 清除多余的数据
      const newScores = {...scores};
      const newConfidences = {...confidences};
      delete newScores[newCount + 1];
      delete newConfidences[newCount + 1];
      setScores(newScores);
      setConfidences(newConfidences);
    }
  };

  // 处理评分变化
  const handleScoreChange = (reviewerIndex, value) => {
    setScores({
      ...scores,
      [reviewerIndex]: value
    });
  };

  // 处理自信心变化
  const handleConfidenceChange = (reviewerIndex, value) => {
    setConfidences({
      ...confidences,
      [reviewerIndex]: value
    });
  };

  const calculateStats = () => {
    const scoreValues = Object.values(scores).filter(s => s).map(Number);

    if (scoreValues.length === 0) {
      return {
        average: '--',
        variance: '--',
        highest: '--',
        lowest: '--',
        positiveCount: 0,
        negativeCount: 0,
        neutralCount: 0
      };
    }

    let sum = 0;
    for (let i = 0; i < scoreValues.length; i++) {
      sum += scoreValues[i];
    }
    const average = sum / scoreValues.length;

    let varianceSum = 0;
    for (let i = 0; i < scoreValues.length; i++) {
      varianceSum += Math.pow(scoreValues[i] - average, 2);
    }
    const variance = varianceSum / scoreValues.length;

    const highest = Math.max.apply(null, scoreValues);
    const lowest = Math.min.apply(null, scoreValues);

    let positiveCount = 0;
    let negativeCount = 0;
    let neutralCount = 0;

    for (let i = 0; i < scoreValues.length; i++) {
      if (scoreValues[i] > 6) {
        positiveCount++;
      } else if (scoreValues[i] < 5) {
        negativeCount++;
      } else {
        neutralCount++;
      }
    }

    return {
      average: average.toFixed(1),
      variance: variance.toFixed(1),
      highest: highest,
      lowest: lowest,
      positiveCount: positiveCount,
      negativeCount: negativeCount,
      neutralCount: neutralCount
    };
  };

  const calculatePrediction = async () => {
    const scoreValues = Object.values(scores).filter(s => s).map(Number);
    const confidenceValues = Object.values(confidences).filter(c => c).map(Number);

    if (scoreValues.length === 0) return null;

    try {
      const apiUrl = getApiBaseUrl();
      const response = await fetch(`${apiUrl}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scores: scoreValues,
          confidences: confidenceValues,
          conference: settings.conference || 'ICLR'
        })
      });

      if (response.ok) {
        const data = await response.json();
        return {
          probability: data.probability,
          avgScore: data.avg_score,
          minScore: data.min_score,
          rankInAll: data.rank_in_all,
          rankInAccepted: data.rank_in_accepted,
          totalPapers: data.total_papers,
          acceptedPapers: data.accepted_papers,
          predictionMethod: data.prediction_method
        };
      } else {
        throw new Error('后端预测失败');
      }
    } catch (error) {
      console.error('预测失败:', error);
      alert('预测失败，请检查网络连接或联系管理员');
      return null;
    }
  };

  const handlePredict = async () => {
    const hasAnyScore = Object.values(scores).some(s => s);

    if (!hasAnyScore) {
      alert('请至少填写一个评审评分！');
      return;
    }

    if (!showPayment) {
      setShowPayment(true);
      // 开始等待倒计时
      setIsWaiting(true);
      setWaitingTime(settings.paymentWaitTime);
      return;
    }
  };

  // 支付处理
  const handlePayment = async () => {
    setIsLoading(true);
    setPaymentStatus('pending');

    // 模拟支付处理时间
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 直接显示预测结果
    setPaymentStatus('success');
    setShowPayment(false);
    setIsLoading(false);

    const result = await calculatePrediction();
    if (result) {
      setPrediction(result);
    }
  };

  const stats = calculateStats();
  const hasScores = Object.values(scores).some(s => s);

  const neuripsData = [
    { year: '2020', acceptance: 25.9 },
    { year: '2021', acceptance: 26.6 },
    { year: '2022', acceptance: 25.6 },
    { year: '2023', acceptance: 31.2 },
    { year: '2024', acceptance: 30.8 },
    { year: '2025', acceptance: 28.5 }
  ];

  return (
    <div className="max-w-5xl mx-auto p-4 bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">{settings.conference || 'NeurIPS'} 论文接受率预测器</h1>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
            <p className="text-gray-700 mb-2">
              🎯 <strong>智能预测系统</strong> - 基于历史数据分析，预测您的论文在顶级会议的接受可能性
            </p>
            <p className="text-sm text-gray-600">
              💡 只需输入评审评分，即可获得专业的接受率分析和排名预测
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-gray-800">{settings.conference || 'ICLR'} 审稿人分数</h3>
                <div className="flex space-x-2">
                  <button
                    onClick={removeReviewer}
                    disabled={reviewerCount <= 1}
                    className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    -
                  </button>
                  <span className="px-3 py-1 bg-gray-200 rounded text-sm">{reviewerCount}个评审</span>
                  <button
                    onClick={addReviewer}
                    disabled={reviewerCount >= 10}
                    className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    +
                  </button>
                </div>
              </div>

              {Array.from({length: reviewerCount}, (_, i) => i + 1).map(reviewerIndex => (
                <div key={reviewerIndex} className="grid grid-cols-2 gap-3 mb-3 p-3 bg-white rounded-lg border">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">评审 {reviewerIndex} 评分</label>
                    <select
                      value={scores[reviewerIndex] || ''}
                      onChange={(e) => handleScoreChange(reviewerIndex, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">请选择评分</option>
                      {settings.scoreOptions && settings.scoreOptions.map(score => (
                        <option key={score} value={score}>{score}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">自信心</label>
                    <select
                      value={confidences[reviewerIndex] || ''}
                      onChange={(e) => handleConfidenceChange(reviewerIndex, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">请选择自信心</option>
                      {settings.confidenceOptions && settings.confidenceOptions.map(conf => (
                        <option key={conf} value={conf}>{conf}</option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}

              {hasScores && (
                <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <h4 className="text-sm font-semibold text-blue-800 mb-2">实时统计</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-white rounded p-2">
                      <span className="text-gray-600">评审均分:</span>
                      <span className="font-bold text-blue-600 ml-2">{stats.average}</span>
                    </div>
                    <div className="bg-white rounded p-2">
                      <span className="text-gray-600">方差:</span>
                      <span className="font-bold text-purple-600 ml-2">{stats.variance}</span>
                    </div>
                    <div className="bg-white rounded p-2">
                      <span className="text-gray-600">最高分:</span>
                      <span className="font-bold text-green-600 ml-2">{stats.highest}</span>
                    </div>
                    <div className="bg-white rounded p-2">
                      <span className="text-gray-600">最低分:</span>
                      <span className="font-bold text-red-600 ml-2">{stats.lowest}</span>
                    </div>
                    <div className="bg-white rounded p-2">
                      <span className="text-gray-600">正分个数(&gt;6):</span>
                      <span className="font-bold text-green-600 ml-2">{stats.positiveCount}</span>
                    </div>
                    <div className="bg-white rounded p-2">
                      <span className="text-gray-600">负分个数(&lt;5):</span>
                      <span className="font-bold text-red-600 ml-2">{stats.negativeCount}</span>
                    </div>
                    <div className="bg-white rounded p-2 col-span-2">
                      <span className="text-gray-600">中间分个数(5,6):</span>
                      <span className="font-bold text-yellow-600 ml-2">{stats.neutralCount}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <button onClick={handlePredict} className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all transform hover:scale-105 shadow-lg">
              {showPayment ? `支付 ¥${settings.price} 后查看结果` : '获取被接受可能性结果'}
            </button>
          </div>

          <div className="space-y-4">
            {showPayment && (
              <div className="bg-green-50 border-2 border-green-400 rounded-lg p-4 text-center">
                <div className="bg-green-500 text-white p-3 rounded-t-lg -mx-4 -mt-4 mb-4">
                  <h3 className="text-lg font-bold">微信扫码支付</h3>
                </div>

                <div className="bg-white p-4 rounded-lg shadow-lg inline-block mb-3">
                  {settings.qrCodeUrl ? (
                    <img
                      src={settings.qrCodeUrl}
                      alt="支付二维码"
                      className="w-40 h-40 object-contain border-2 border-gray-300 rounded-lg mb-3"
                    />
                  ) : (
                    <div className="w-40 h-40 bg-gray-200 border-2 border-gray-300 rounded-lg flex items-center justify-center mb-3">
                      <div className="text-center">
                        <div className="text-3xl mb-2">📱</div>
                        <div className="text-sm text-gray-600">微信二维码</div>
                        <div className="text-xs text-gray-500 mt-1">管理员未上传</div>
                      </div>
                    </div>
                  )}
                  <div className="text-center">
                    <div className="flex items-center justify-center mb-2">
                      <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center mr-2">
                        <span className="text-white text-xs">✓</span>
                      </div>
                      <span className="font-bold">微信支付</span>
                    </div>
                  </div>
                </div>

                <div className="text-xl font-bold text-green-600 mb-3">¥{settings.price}</div>
                <div className="text-sm text-yellow-600 mb-3">
                  ⚠️ 请确认支付金额不少于 ¥{settings.price}
                </div>
                <p className="text-green-700 mb-3">扫描二维码完成支付</p>

                {isWaiting ? (
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-green-500 mb-2"></div>
                    <p className="text-sm text-gray-600">
                      正在等待确认支付... {waitingTime}秒
                    </p>
                  </div>
                ) : isLoading ? (
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-green-500 mb-2"></div>
                    <p className="text-sm text-gray-600">等待支付确认...</p>
                  </div>
                ) : (
                  <button
                    onClick={handlePayment}
                    className="px-6 py-2 bg-green-500 text-white rounded-lg font-semibold hover:bg-green-600 transition-colors"
                  >
                    确认支付
                  </button>
                )}
                <p className="text-xs text-green-600 mt-2">支付完成后页面将自动显示结果</p>
              </div>
            )}

            {prediction && (
              <>
                <div className="bg-gradient-to-r from-green-100 to-blue-100 border-2 border-green-300 rounded-xl p-6 text-center shadow-lg">
                  <h2 className="text-xl font-bold text-gray-800 mb-3">接受可能性为：</h2>
                  <div className="text-5xl font-bold text-green-600 mb-3">
                    {(prediction.probability * 100).toFixed(1)}%
                  </div>
                  <div className="grid grid-cols-3 gap-3 mt-4">
                    <div className="bg-white rounded-lg p-2 shadow">
                      <div className="text-xs font-medium text-gray-600">平均评分</div>
                      <div className="text-lg font-bold text-blue-600">
                        {prediction.avgScore ? prediction.avgScore.toFixed(1) : '--'}
                      </div>
                    </div>
                    <div className="bg-white rounded-lg p-2 shadow">
                      <div className="text-xs font-medium text-gray-600">最低评分</div>
                      <div className="text-lg font-bold text-red-600">
                        {prediction.minScore || '--'}
                      </div>
                    </div>
                    <div className="bg-white rounded-lg p-2 shadow">
                      <div className="text-xs font-medium text-gray-600">预测置信度</div>
                      <div className="text-lg font-bold text-purple-600">高</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg p-4 border shadow">
                  <h3 className="text-base font-semibold mb-3 text-gray-800">论文位次分析</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="bg-blue-50 rounded-lg p-3">
                      <h4 className="font-semibold text-blue-800 mb-1 text-sm">在全体论文中的位次</h4>
                      <div className="text-xl font-bold text-blue-600 mb-1">
                        第 {prediction.rankInAll ? prediction.rankInAll.toLocaleString() : '--'} 名
                      </div>
                      <div className="text-xs text-gray-600">
                        / 共 {prediction.totalPapers ? prediction.totalPapers.toLocaleString() : historicalStats.totalPapers.toLocaleString()} 篇投稿
                      </div>
                    </div>
                    <div className="bg-green-50 rounded-lg p-3">
                      <h4 className="font-semibold text-green-800 mb-1 text-sm">在接收论文中的位次</h4>
                      <div className="text-xl font-bold text-green-600 mb-1">
                        第 {prediction.rankInAccepted ? prediction.rankInAccepted.toLocaleString() : '--'} 名
                      </div>
                      <div className="text-xs text-gray-600">
                        / 共 {prediction.acceptedPapers ? prediction.acceptedPapers.toLocaleString() : historicalStats.acceptedPapers.toLocaleString()} 篇接收
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            <div className="bg-white rounded-lg p-4 border shadow">
              <h3 className="text-base font-semibold mb-3 text-gray-800">{settings.conference || 'ICLR'}历史接受率</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={neuripsData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis domain={[20, 35]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="acceptance" stroke="#8884d8" strokeWidth={3} dot={{ fill: '#8884d8', strokeWidth: 2, r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
              <div className="mt-2 text-sm text-gray-600 text-center">
                近年来{settings.conference || 'ICLR'}接受率约为 {(historicalStats.acceptanceRate * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

        <div className="text-center mt-6 py-3 border-t border-gray-200">
          <p className="text-gray-600 text-sm">
            有问题？联系
            <button
              onClick={() => {
                navigator.clipboard.writeText(settings.contactPhone).then(() => {
                  alert(`✅ 客服微信号已复制: ${settings.contactPhone}\n请打开微信添加好友！`);
                }).catch(() => {
                  alert(`📱 客服微信号: ${settings.contactPhone}\n请手动复制添加微信好友！`);
                });
              }}
              className="font-bold text-blue-600 hover:text-blue-800 underline decoration-2 underline-offset-2 mx-1 transition-colors"
            >
              客服微信
            </button>
            获取帮助
          </p>
          <p className="text-xs text-gray-400 mt-1">点击"客服微信"自动复制微信号</p>
        </div>
      </div>
    </div>
  );
}