# backend/models/train_model.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib


def train_model(data_path):
    # 加载你的评审数据
    df = pd.read_csv(data_path)

    # 特征工程
    X = df[['avg_score', 'min_score', 'max_score', 'num_reviews', 'avg_confidence']]
    y = df['accepted']  # 0 or 1

    # 训练模型
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)

    # 保存模型
    joblib.dump(model, 'models/neurips_model.pkl')
    print(f"模型准确率: {model.score(X_test, y_test):.3f}")

# 运行训练
# train_model('your_review_data.csv')