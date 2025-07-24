#!/usr/bin/env python3
"""
高级机器学习预测模型
基于真实ICLR数据训练的接受率预测模型
"""

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class PaperAcceptancePredictor:
    """论文接受率预测器"""
    
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        
        # 初始化模型
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'logistic_regression': LogisticRegression(
                random_state=42,
                max_iter=1000
            )
        }
        
        self.scaler = StandardScaler()
        self.feature_names = []
        self.trained_models = {}
        self.ensemble_weights = {}
        
    def extract_features(self, papers_data):
        """
        从论文数据中提取特征
        
        Args:
            papers_data: 论文数据列表
            
        Returns:
            DataFrame: 特征矩阵
            Series: 标签向量 (1=接受, 0=拒绝)
        """
        
        features_list = []
        labels_list = []
        
        for paper in papers_data:
            try:
                # 提取评审分数
                scores = []
                confidences = []
                
                for review in paper.get('reviews', []):
                    rating = review.get('rating', '-1')
                    confidence = review.get('confidence', '-1')
                    
                    if rating != '-1':
                        try:
                            score = float(rating)
                            if 1 <= score <= 10:
                                scores.append(score)
                        except:
                            pass
                    
                    if confidence != '-1':
                        try:
                            conf = float(confidence)
                            if 1 <= conf <= 5:
                                confidences.append(conf)
                        except:
                            pass
                
                # 如果没有有效评分，跳过
                if not scores:
                    continue
                
                # 计算基础特征
                features = {}
                
                # 评分统计特征
                features['avg_score'] = np.mean(scores)
                features['min_score'] = np.min(scores)
                features['max_score'] = np.max(scores)
                features['std_score'] = np.std(scores) if len(scores) > 1 else 0
                features['median_score'] = np.median(scores)
                features['score_range'] = np.max(scores) - np.min(scores)
                
                # 评分分布特征
                features['num_reviews'] = len(scores)
                features['high_scores'] = sum(1 for s in scores if s >= 7)  # 高分数量
                features['low_scores'] = sum(1 for s in scores if s <= 4)   # 低分数量
                features['mid_scores'] = sum(1 for s in scores if 4 < s < 7) # 中等分数量
                
                # 评分比例特征
                features['high_score_ratio'] = features['high_scores'] / len(scores)
                features['low_score_ratio'] = features['low_scores'] / len(scores)
                features['mid_score_ratio'] = features['mid_scores'] / len(scores)
                
                # 自信心特征
                if confidences:
                    features['avg_confidence'] = np.mean(confidences)
                    features['min_confidence'] = np.min(confidences)
                    features['max_confidence'] = np.max(confidences)
                    features['std_confidence'] = np.std(confidences) if len(confidences) > 1 else 0
                else:
                    features['avg_confidence'] = 3.0  # 默认中等自信心
                    features['min_confidence'] = 3.0
                    features['max_confidence'] = 3.0
                    features['std_confidence'] = 0.0
                
                # 高级特征
                features['score_confidence_corr'] = np.corrcoef(scores[:len(confidences)], confidences)[0,1] if len(confidences) > 1 else 0
                features['weighted_score'] = sum(s * c for s, c in zip(scores[:len(confidences)], confidences)) / sum(confidences) if confidences else features['avg_score']
                
                # 论文质量指标
                features['consistency_score'] = 1.0 / (1.0 + features['std_score'])  # 评分一致性
                features['controversial_score'] = features['score_range'] / 10.0      # 争议性
                
                # 决策边界特征
                features['above_threshold_6'] = 1 if features['avg_score'] >= 6 else 0
                features['above_threshold_7'] = 1 if features['avg_score'] >= 7 else 0
                features['no_reject_score'] = 1 if features['min_score'] >= 5 else 0
                
                # 提取标签
                decision = paper.get('paper_decision', '')
                is_accepted = 1 if 'accept' in decision.lower() else 0
                
                features_list.append(features)
                labels_list.append(is_accepted)
                
            except Exception as e:
                print(f"⚠️  处理论文特征时出错: {e}")
                continue
        
        # 转换为DataFrame
        if not features_list:
            raise ValueError("没有提取到有效特征")
        
        features_df = pd.DataFrame(features_list)
        labels_series = pd.Series(labels_list)
        
        # 保存特征名称
        self.feature_names = list(features_df.columns)
        
        print(f"✅ 特征提取完成: {len(features_df)} 个样本, {len(self.feature_names)} 个特征")
        print(f"📊 正负样本比例: {labels_series.mean():.2%} 接受率")
        
        return features_df, labels_series
    
    def train_models(self, features_df, labels_series, test_size=0.2):
        """
        训练所有模型
        
        Args:
            features_df: 特征矩阵
            labels_series: 标签向量
            test_size: 测试集比例
            
        Returns:
            dict: 模型性能报告
        """
        
        print("🎯 开始训练模型...")
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            features_df, labels_series, 
            test_size=test_size, 
            random_state=42, 
            stratify=labels_series
        )
        
        # 特征标准化
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # 训练单个模型
        performance_report = {}
        
        for model_name, model in self.models.items():
            print(f"🔄 训练 {model_name}...")
            
            # 训练模型
            if model_name == 'logistic_regression':
                model.fit(X_train_scaled, y_train)
                y_pred = model.predict(X_test_scaled)
                y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            else:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                y_pred_proba = model.predict_proba(X_test)[:, 1]
            
            # 计算性能指标
            performance = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1': f1_score(y_test, y_pred),
                'auc': roc_auc_score(y_test, y_pred_proba)
            }
            
            # 交叉验证
            if model_name == 'logistic_regression':
                cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            else:
                cv_scores = cross_val_score(model, X_train, y_train, cv=5)
            
            performance['cv_mean'] = cv_scores.mean()
            performance['cv_std'] = cv_scores.std()
            
            performance_report[model_name] = performance
            self.trained_models[model_name] = model
            
            print(f"   ✅ {model_name}: 准确率={performance['accuracy']:.3f}, AUC={performance['auc']:.3f}")
        
        # 计算集成权重（基于AUC性能）
        total_auc = sum(perf['auc'] for perf in performance_report.values())
        self.ensemble_weights = {
            name: perf['auc'] / total_auc 
            for name, perf in performance_report.items()
        }
        
        print(f"📊 集成权重: {self.ensemble_weights}")
        
        # 保存模型
        self.save_models()
        
        return performance_report
    
    def predict_single(self, scores, confidences=None):
        """
        预测单篇论文的接受概率
        
        Args:
            scores: 评分列表
            confidences: 自信心列表（可选）
            
        Returns:
            dict: 预测结果
        """
        
        if not self.trained_models:
            raise ValueError("模型尚未训练，请先调用 train_models()")
        
        # 构造特征
        if not confidences:
            confidences = [3.0] * len(scores)  # 默认中等自信心
        
        # 确保长度一致
        min_len = min(len(scores), len(confidences))
        scores = scores[:min_len]
        confidences = confidences[:min_len]
        
        features = {}
        
        # 基础统计特征
        features['avg_score'] = np.mean(scores)
        features['min_score'] = np.min(scores)
        features['max_score'] = np.max(scores)
        features['std_score'] = np.std(scores) if len(scores) > 1 else 0
        features['median_score'] = np.median(scores)
        features['score_range'] = np.max(scores) - np.min(scores)
        
        # 评分分布特征
        features['num_reviews'] = len(scores)
        features['high_scores'] = sum(1 for s in scores if s >= 7)
        features['low_scores'] = sum(1 for s in scores if s <= 4)
        features['mid_scores'] = sum(1 for s in scores if 4 < s < 7)
        
        features['high_score_ratio'] = features['high_scores'] / len(scores)
        features['low_score_ratio'] = features['low_scores'] / len(scores)
        features['mid_score_ratio'] = features['mid_scores'] / len(scores)
        
        # 自信心特征
        features['avg_confidence'] = np.mean(confidences)
        features['min_confidence'] = np.min(confidences)
        features['max_confidence'] = np.max(confidences)
        features['std_confidence'] = np.std(confidences) if len(confidences) > 1 else 0
        
        # 高级特征
        features['score_confidence_corr'] = np.corrcoef(scores, confidences)[0,1] if len(scores) > 1 else 0
        features['weighted_score'] = sum(s * c for s, c in zip(scores, confidences)) / sum(confidences)
        features['consistency_score'] = 1.0 / (1.0 + features['std_score'])
        features['controversial_score'] = features['score_range'] / 10.0
        features['above_threshold_6'] = 1 if features['avg_score'] >= 6 else 0
        features['above_threshold_7'] = 1 if features['avg_score'] >= 7 else 0
        features['no_reject_score'] = 1 if features['min_score'] >= 5 else 0
        
        # 转换为DataFrame
        feature_vector = pd.DataFrame([features])[self.feature_names]
        
        # 获取各模型预测
        predictions = {}
        
        for model_name, model in self.trained_models.items():
            if model_name == 'logistic_regression':
                feature_scaled = self.scaler.transform(feature_vector)
                prob = model.predict_proba(feature_scaled)[0, 1]
            else:
                prob = model.predict_proba(feature_vector)[0, 1]
            
            predictions[model_name] = prob
        
        # 集成预测
        ensemble_prob = sum(
            predictions[name] * weight 
            for name, weight in self.ensemble_weights.items()
        )
        
        return {
            'ensemble_probability': ensemble_prob,
            'individual_predictions': predictions,
            'features_used': features,
            'confidence_level': 'high' if features['std_score'] < 1.0 else 'medium'
        }
    
    def save_models(self):
        """保存训练好的模型"""
        
        model_info = {
            'feature_names': self.feature_names,
            'ensemble_weights': self.ensemble_weights,
            'training_date': datetime.now().isoformat()
        }
        
        # 保存模型文件
        for name, model in self.trained_models.items():
            joblib.dump(model, os.path.join(self.models_dir, f"{name}.pkl"))
        
        # 保存标准化器
        joblib.dump(self.scaler, os.path.join(self.models_dir, "scaler.pkl"))
        
        # 保存模型信息
        with open(os.path.join(self.models_dir, "model_info.json"), 'w') as f:
            json.dump(model_info, f, indent=2)
        
        print(f"💾 模型已保存到 {self.models_dir}")
    
    def load_models(self):
        """加载预训练模型"""
        
        try:
            # 加载模型信息
            with open(os.path.join(self.models_dir, "model_info.json"), 'r') as f:
                model_info = json.load(f)
            
            self.feature_names = model_info['feature_names']
            self.ensemble_weights = model_info['ensemble_weights']
            
            # 加载模型
            for name in self.ensemble_weights.keys():
                model_path = os.path.join(self.models_dir, f"{name}.pkl")
                self.trained_models[name] = joblib.load(model_path)
            
            # 加载标准化器
            self.scaler = joblib.load(os.path.join(self.models_dir, "scaler.pkl"))
            
            print(f"✅ 模型加载成功 (训练时间: {model_info.get('training_date', 'Unknown')})")
            return True
            
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return False

def train_predictor_from_data(data_files):
    """
    从数据文件训练预测器
    
    Args:
        data_files: 数据文件路径列表
        
    Returns:
        PaperAcceptancePredictor: 训练好的预测器
    """
    
    print("🚀 开始训练论文接受率预测模型")
    print("=" * 50)
    
    # 加载数据
    all_papers = []
    for data_file in data_files:
        if not os.path.exists(data_file):
            print(f"⚠️  数据文件不存在: {data_file}")
            continue
        
        print(f"📖 加载数据文件: {data_file}")
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    all_papers.append(json.loads(line.strip()))
    
    if not all_papers:
        raise ValueError("没有找到有效的训练数据")
    
    print(f"📊 总数据量: {len(all_papers)} 篇论文")
    
    # 创建预测器
    predictor = PaperAcceptancePredictor()
    
    # 提取特征
    features_df, labels_series = predictor.extract_features(all_papers)
    
    # 训练模型
    performance_report = predictor.train_models(features_df, labels_series)
    
    # 打印性能报告
    print("\n📈 模型性能报告:")
    print("=" * 50)
    for model_name, metrics in performance_report.items():
        print(f"{model_name}:")
        print(f"  准确率: {metrics['accuracy']:.3f}")
        print(f"  精确率: {metrics['precision']:.3f}")
        print(f"  召回率: {metrics['recall']:.3f}")
        print(f"  F1分数: {metrics['f1']:.3f}")
        print(f"  AUC: {metrics['auc']:.3f}")
        print(f"  交叉验证: {metrics['cv_mean']:.3f} ± {metrics['cv_std']:.3f}")
        print()
    
    return predictor

def main():
    """主函数 - 训练模型"""
    
    # 数据文件列表
    data_files = [
        "nips_history_data/ICLR_2024_formatted.jsonl",
        "nips_history_data/ICLR_2025_formatted.jsonl"
    ]
    
    try:
        # 训练模型
        predictor = train_predictor_from_data(data_files)
        
        # 测试预测
        print("\n🧪 测试预测功能:")
        print("-" * 30)
        
        test_cases = [
            ([8, 7, 9, 8], [4, 3, 5, 4], "高质量论文"),
            ([5, 4, 6, 5], [3, 2, 3, 3], "中等质量论文"),
            ([3, 2, 4, 3], [2, 1, 2, 2], "低质量论文"),
            ([8, 3, 7, 6], [5, 2, 4, 3], "争议性论文")
        ]
        
        for scores, confidences, description in test_cases:
            result = predictor.predict_single(scores, confidences)
            print(f"{description}: {result['ensemble_probability']:.1%} 接受概率")
        
        print("\n🎉 模型训练完成！")
        print("💡 现在可以在 main.py 中使用这个高级预测模型了")
        
    except Exception as e:
        print(f"❌ 训练失败: {e}")

if __name__ == "__main__":
    main()