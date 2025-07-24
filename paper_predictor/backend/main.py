from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import shutil
import json
import uuid
import time
import numpy as np
from datetime import datetime
import random
import requests

app = FastAPI(
    title="论文接受率预测API",
    description="基于规则算法的论文接受率预测系统",
    version="2.0.0"
)

# 创建目录
os.makedirs("uploads/qr_codes", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("nips_history_data", exist_ok=True)  # 历史数据目录

# 修复1：更灵活的CORS配置 - 支持部署环境
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 本地开发
        "http://127.0.0.1:3000",  # 本地开发
        "https://products-silk-chi.vercel.app",  # 🔥 你的Vercel前端URL
        "https://*.vercel.app",  # 所有Vercel子域名
        "*"  # 临时允许所有域名，生产环境建议限制
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 全局设置存储
SETTINGS_FILE = "data/settings.json"
PAYMENTS_FILE = "data/payments.json"

# 默认设置
DEFAULT_SETTINGS = {
    "price": 0.2,
    "qr_code_url": "",
    "contact_phone": "13109973548",
    "score_options": [1, 3, 5, 6, 8, 10],
    "confidence_options": [1, 2, 3, 4, 5],
    "conference": "ICLR",
    "year": "2024",
    "payment_wait_time": 60  # 新增：支付等待时间
}

# 支付订单存储
payments = {}

# 预测统计
prediction_stats = {
    "total_predictions": 0,
    "avg_prediction_time": 0
}

# Google Drive下载链接
ICLR_2024_URL = "https://drive.google.com/uc?export=download&id=1CVsi7YU6rNcrhNqPMrGOWsxqHpsmysH4"
ICLR_2025_URL = "https://drive.google.com/uc?export=download&id=1NXYIG-UIQUnur24fe36fqaobl722pCr_"

# 本地文件路径
ICLR_2024_FILE = "nips_history_data/ICLR_2024_formatted.jsonl"
ICLR_2025_FILE = "nips_history_data/ICLR_2025_formatted.jsonl"


def download_data_from_google_drive():
    """从Google Drive下载数据文件（仅在服务器启动时执行一次）"""

    # Google Drive下载链接
    files_to_download = {
        "nips_history_data/ICLR_2024_formatted.jsonl": "https://drive.google.com/uc?export=download&id=1CVsi7YU6rNcrhNqPMrGOWsxqHpsmysH4",
        "nips_history_data/ICLR_2025_formatted.jsonl": "https://drive.google.com/uc?export=download&id=1NXYIG-UIQUnur24fe36fqaobl722pCr_"
    }

    print("🌐 检查历史数据文件...")

    for file_path, download_url in files_to_download.items():
        if not os.path.exists(file_path):
            print(f"📥 下载 {file_path}...")
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(download_url, timeout=600, stream=True, headers=headers, allow_redirects=True)
                response.raise_for_status()

                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # 保存文件
                with open(file_path, 'wb') as f:
                    f.write(response.content)

                print(f"✅ {file_path} 下载成功 ({len(response.content) / 1024 / 1024:.1f} MB)")

            except Exception as e:
                print(f"❌ {file_path} 下载失败: {e}")
        else:
            print(f"✅ {file_path} 已存在，跳过下载")


# 全局历史数据缓存
historical_data = {}


def load_historical_data():
    """加载历史评审数据"""
    global historical_data
    print("📊 开始加载历史数据...")
    print("🔍 当前工作目录:", os.getcwd())
    print("🔍 检查文件存在:")
    for year, file_path in [("2024", ICLR_2024_FILE), ("2025", ICLR_2025_FILE)]:
        exists = os.path.exists(file_path)
        if exists:
            size = os.path.getsize(file_path)
            print(f"  ✅ {file_path}: {size/1024/1024:.1f}MB")
        else:
            print(f"  ❌ {file_path}: 不存在")

    for year, file_path in [("2024", ICLR_2024_FILE), ("2025", ICLR_2025_FILE)]:
        if os.path.exists(file_path):
            try:
                papers = []
                print(f"📖 读取文件: {file_path}")

                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line:
                            try:
                                paper = json.loads(line)
                                papers.append(paper)
                            except json.JSONDecodeError as e:
                                print(f"⚠️  跳过第{line_num}行，JSON解析错误: {e}")
                                continue

                if not papers:
                    print(f"❌ {file_path} 没有有效数据")
                    continue

                # 计算每篇论文的平均分并分类
                all_papers_with_avg = []
                accepted_papers_with_avg = []

                for paper in papers:
                    scores = extract_paper_scores(paper)
                    if scores:  # 只处理有评分的论文
                        avg_score = np.mean(scores)
                        paper_with_avg = {
                            'avg_score': avg_score,
                            'scores': scores,
                            'decision': paper.get('paper_decision', '').lower()
                        }
                        all_papers_with_avg.append(paper_with_avg)

                        # 判断是否被接受
                        decision = paper.get('paper_decision', '').lower()
                        if 'accept' in decision:
                            accepted_papers_with_avg.append(paper_with_avg)

                # 按平均分降序排序
                all_papers_with_avg.sort(key=lambda x: x['avg_score'], reverse=True)
                accepted_papers_with_avg.sort(key=lambda x: x['avg_score'], reverse=True)

                historical_data[year] = {
                    "all_papers": all_papers_with_avg,
                    "accepted_papers": accepted_papers_with_avg,
                    "total_count": len(all_papers_with_avg),
                    "accepted_count": len(accepted_papers_with_avg),
                    "acceptance_rate": len(accepted_papers_with_avg) / len(
                        all_papers_with_avg) if all_papers_with_avg else 0
                }

                print(
                    f"✅ {year} 年数据: {len(all_papers_with_avg)} 篇有效论文, 接受 {len(accepted_papers_with_avg)} 篇, 接受率 {historical_data[year]['acceptance_rate']:.2%}")

            except Exception as e:
                print(f"❌ 加载 {year} 年数据失败: {e}")
        else:
            print(f"⚠️  未找到 {year} 年数据文件: {file_path}")

    if not historical_data:
        print("❌ 没有加载到任何历史数据，将使用默认算法")
    else:
        print(f"🎉 成功加载 {len(historical_data)} 年的历史数据")


def extract_paper_scores(paper):
    """从论文数据中提取评分信息"""
    scores = []
    if 'reviews' in paper and paper['reviews']:
        for review in paper['reviews']:
            rating = review.get('rating', '')
            rating = rating.split(':')[0]
            # 解析评分
            if rating and rating != '-1':
                try:
                    score = float(rating)
                    if 1 <= score <= 10:
                        scores.append(score)
                except:
                    pass
    return scores


def calculate_paper_ranking_basic(target_scores, target_confidences, year="2025"):
    """基于规则的论文接受率预测"""
    print(f"🔍 收到预测请求 - 评分: {target_scores}, 自信心: {target_confidences}, 年份: {year}")

    if not target_scores:
        print("❌ 没有评分数据")
        return {
            "probability": 0.0,
            "rank_in_all": 10000,
            "rank_in_accepted": 2500,
            "total_papers": 12000,
            "accepted_papers": 3000,
            "prediction_method": "rule_threshold"
        }

    # 计算用户论文的基本统计
    user_avg_score = np.mean(target_scores)
    positive_scores = sum(1 for score in target_scores if score >= 5)
    negative_scores = sum(1 for score in target_scores if score < 5)

    print(f"📊 用户论文统计 - 平均分: {user_avg_score:.2f}, 正分数: {positive_scores}, 负分数: {negative_scores}")

    # 规则判断概率
    final_probability = 0.5  # 默认概率

    # 规则1: 均值 > 6
    if user_avg_score > 6:
        final_probability = random.uniform(0.85, 0.95)
        print(f"✅ 规则1命中: 均值{user_avg_score:.2f} > 6, 概率: {final_probability:.3f}")
    # 规则2: 均值 <= 4
    elif user_avg_score <= 4:
        final_probability = random.uniform(0.01, 0.2)
        print(f"❌ 规则2命中: 均值{user_avg_score:.2f} <= 4, 概率: {final_probability:.3f}")
    # 规则3: 全是正分（>=5）
    elif negative_scores == 0:
        final_probability = random.uniform(0.85, 0.95)
        print(f"✅ 规则3命中: 全是正分, 概率: {final_probability:.3f}")
    # 规则4: 全是负分（<5）
    elif positive_scores == 0:
        final_probability = random.uniform(0.1, 0.25)
        print(f"❌ 规则4命中: 全是负分, 概率: {final_probability:.3f}")
    # 规则5: 负分个数 > 正分个数
    elif negative_scores > positive_scores:
        final_probability = random.uniform(0.1, 0.35)
        print(f"❌ 规则5命中: 负分({negative_scores}) > 正分({positive_scores}), 概率: {final_probability:.3f}")
    # 规则6: 三个或更多负分
    elif negative_scores >= 3:
        final_probability = random.uniform(0.01, 0.22)
        print(f"❌ 规则6命中: {negative_scores}个负分, 概率: {final_probability:.3f}")
    # 规则7: 只有一个负分且均值 > 5
    elif negative_scores == 1 and user_avg_score > 5:
        final_probability = random.uniform(0.80, 0.90)
        print(f"✅ 规则7命中: 1个负分且均值{user_avg_score:.2f} > 5, 概率: {final_probability:.3f}")
    # 规则8: 有两个负分
    elif negative_scores == 2:
        final_probability = random.uniform(0.60, 0.75)
        print(f"⚠️  规则8命中: 2个负分, 概率: {final_probability:.3f}")
    # 规则9: 分数只有5和6
    elif all(score in [5, 6] for score in target_scores):
        final_probability = random.uniform(0.75, 0.85)
        print(f"✅ 规则9命中: 全是5,6分, 概率: {final_probability:.3f}")
    # 默认情况：基于均值线性插值
    else:
        if user_avg_score >= 5:
            final_probability = (user_avg_score - 4) / (6 - 4) * (0.75 - 0.25) + 0.25
        else:
            final_probability = 0.25
        print(f"📐 默认线性插值: 均值{user_avg_score:.2f}, 概率: {final_probability:.3f}")

    # 修复2：确保从正确的历史数据计算排名
    prev_year = str(int(year) - 1)  # 预测年份的前一年作为参考数据

    if prev_year in historical_data and historical_data[prev_year]["all_papers"]:
        print(f"📈 使用 {prev_year} 年历史数据计算排名")

        all_papers = historical_data[prev_year]["all_papers"]
        accepted_papers = historical_data[prev_year]["accepted_papers"]

        # 计算在所有论文中的排名：比用户均分高的论文数量 + 1
        rank_in_all = 1
        for paper in all_papers:
            if paper['avg_score'] > user_avg_score:
                rank_in_all += 1
            else:
                break  # 因为已经按降序排序，可以提前退出

        # 计算在接受论文中的排名
        rank_in_accepted = 1
        for paper in accepted_papers:
            if paper['avg_score'] > user_avg_score:
                rank_in_accepted += 1
            else:
                break

        total_papers = len(all_papers)
        accepted_papers_count = len(accepted_papers)

        print(f"🏆 排名计算完成:")
        print(f"  - 在所有论文中: 第 {rank_in_all} 名 / 共 {total_papers} 篇")
        print(f"  - 在接受论文中: 第 {rank_in_accepted} 名 / 共 {accepted_papers_count} 篇")
        print(f"  - 用户平均分 {user_avg_score:.2f} 在历史数据中的位置")

    else:
        print(f"⚠️  未找到 {prev_year} 年历史数据，使用默认排名")
        # 使用默认值
        total_papers = 12000
        accepted_papers_count = 3000
        # 基于概率估算排名作为备用
        rank_in_all = max(1, int(total_papers * (1 - final_probability)))
        rank_in_accepted = max(1, int(accepted_papers_count * (1 - final_probability)))

    result = {
        "probability": final_probability,
        "rank_in_all": rank_in_all,
        "rank_in_accepted": rank_in_accepted,
        "total_papers": total_papers,
        "accepted_papers": accepted_papers_count,
        "prediction_method": "rule_threshold_with_historical_ranking"
    }

    print(f"🎯 最终结果: {result}")
    return result


def load_settings():
    """加载设置"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载设置失败: {e}")
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """保存设置"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存设置失败: {e}")
        return False


def load_payments():
    """加载支付记录"""
    global payments
    try:
        if os.path.exists(PAYMENTS_FILE):
            with open(PAYMENTS_FILE, 'r', encoding='utf-8') as f:
                payments = json.load(f)
    except Exception as e:
        print(f"加载支付记录失败: {e}")
        payments = {}


def save_payments():
    """保存支付记录"""
    try:
        with open(PAYMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(payments, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存支付记录失败: {e}")
        return False


# 启动时加载数据
current_settings = load_settings()
load_payments()
download_data_from_google_drive()  # 🔥 添加这行
load_historical_data()  # 加载历史数据


# 数据模型
class PredictionRequest(BaseModel):
    scores: List[float]
    confidences: List[float] = []
    conference: str = "ICLR"


class PredictionResponse(BaseModel):
    probability: float
    rank_in_all: int
    rank_in_accepted: int
    avg_score: float
    min_score: float
    total_papers: int
    accepted_papers: int
    prediction_method: str = "rule_threshold"
    prediction_time_ms: Optional[int] = None


class SettingsUpdate(BaseModel):
    price: float
    contact_phone: str
    score_options: str
    confidence_options: str
    conference: Optional[str] = "ICLR"
    year: Optional[str] = "2024"
    payment_wait_time: Optional[int] = 60  # 新增：支付等待时间


class PaymentOrder(BaseModel):
    amount: float
    description: str


class PaymentResponse(BaseModel):
    orderId: str
    amount: float
    status: str = "pending"


@app.get("/")
async def root():
    return {
        "message": "论文接受率预测API正在运行",
        "version": "2.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "ml_models": False,
            "prediction_method": "rule_based",
            "prediction_stats": prediction_stats,
            "historical_data_loaded": list(historical_data.keys())  # 修复：返回已加载的数据年份
        }
    }


@app.get("/settings")
async def get_settings():
    """获取当前设置"""
    return current_settings


@app.post("/settings")
async def update_settings(new_settings: SettingsUpdate):
    """更新设置"""
    global current_settings

    try:
        # 解析评分选项
        score_options = [float(x.strip()) for x in new_settings.score_options.split(',') if x.strip()]
        confidence_options = [float(x.strip()) for x in new_settings.confidence_options.split(',') if x.strip()]
        # 更新设置
        current_settings.update({
            "price": new_settings.price,
            "contact_phone": new_settings.contact_phone,
            "score_options": score_options,
            "confidence_options": confidence_options,
            "conference": new_settings.conference or current_settings.get("conference", "ICLR"),
            "year": new_settings.year or current_settings.get("year", "2024"),
            "payment_wait_time": new_settings.payment_wait_time or current_settings.get("payment_wait_time", 60)
        })

        # 保存到文件
        success = save_settings(current_settings)

        if success:
            return {"message": "设置已更新", "settings": current_settings}
        else:
            raise HTTPException(status_code=500, detail="保存设置失败")

    except ValueError as e:
        raise HTTPException(status_code=400, detail="评分选项格式错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新设置失败: {str(e)}")


@app.post("/upload-qr")
async def upload_qr_code(file: UploadFile = File(...)):
    """上传支付二维码"""
    try:
        # 验证文件类型
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"qr_{int(time.time())}{file_extension}"
        file_path = f"uploads/qr_codes/{unique_filename}"

        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 更新设置中的二维码URL
        qr_url = f"/uploads/qr_codes/{unique_filename}"
        current_settings["qr_code_url"] = qr_url
        save_settings(current_settings)

        return {"qr_code_url": qr_url, "message": "二维码上传成功"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.post("/create-payment", response_model=PaymentResponse)
async def create_payment_order(order: PaymentOrder):
    """创建支付订单"""
    try:
        order_id = str(uuid.uuid4())
        payment_data = {
            "orderId": order_id,
            "amount": order.amount,
            "description": order.description,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "expires_at": datetime.fromtimestamp(time.time() + 1800).isoformat()  # 30分钟后过期
        }

        # 保存订单
        payments[order_id] = payment_data
        save_payments()

        return PaymentResponse(
            orderId=order_id,
            amount=order.amount,
            status="pending"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建支付订单失败: {str(e)}")


@app.get("/check-payment/{order_id}")
async def check_payment_status(order_id: str):
    """检查支付状态"""
    if order_id not in payments:
        raise HTTPException(status_code=404, detail="订单不存在")

    payment = payments[order_id]

    # 检查是否过期
    expires_at = datetime.fromisoformat(payment["expires_at"])
    if datetime.now() > expires_at:
        payment["status"] = "expired"
        payments[order_id] = payment
        save_payments()

    # 模拟支付成功概率（实际应该调用真实支付API）
    created_at = datetime.fromisoformat(payment["created_at"])
    elapsed = (datetime.now() - created_at).total_seconds()

    if elapsed > 10 and payment["status"] == "pending":
        import random
        if random.random() < 0.8:  # 80%概率成功
            payment["status"] = "success"
            payment["paid_at"] = datetime.now().isoformat()
        else:
            payment["status"] = "failed"

        payments[order_id] = payment
        save_payments()

    return {"status": payment["status"], "order_id": order_id}


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """预测论文接受率"""
    print(f"\n🚀 收到预测请求: {request}")

    if not request.scores:
        raise HTTPException(status_code=400, detail="请提供评分")

    try:
        start_time = time.time()

        # 基本统计
        avg_score = np.mean(request.scores)
        min_score = min(request.scores)

        print(f"📊 基本统计 - 平均分: {avg_score:.2f}, 最低分: {min_score}")

        # 使用基础规则计算排名，传递年份信息
        year = current_settings.get("year", "2025")
        ranking_result = calculate_paper_ranking_basic(request.scores, request.confidences, year)

        # 计算预测时间
        prediction_time = time.time() - start_time
        prediction_stats["total_predictions"] += 1
        prediction_stats["avg_prediction_time"] = (
                                                          prediction_stats["avg_prediction_time"] * (
                                                          prediction_stats["total_predictions"] - 1) +
                                                          prediction_time
                                                  ) / prediction_stats["total_predictions"]

        response = PredictionResponse(
            probability=ranking_result["probability"],
            rank_in_all=ranking_result["rank_in_all"],
            rank_in_accepted=ranking_result["rank_in_accepted"],
            avg_score=avg_score,
            min_score=min_score,
            total_papers=ranking_result["total_papers"],
            accepted_papers=ranking_result["accepted_papers"],
            prediction_method=ranking_result["prediction_method"],
            prediction_time_ms=int(prediction_time * 1000)
        )

        print(f"✅ 预测完成: 概率={response.probability:.3f}, 用时={response.prediction_time_ms}ms")
        return response

    except Exception as e:
        print(f"❌ 预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@app.get("/data-status")
async def get_data_status():
    """获取数据加载状态"""
    return {
        "historical_data_loaded": list(historical_data.keys()),
        "data_details": {
            year: {
                "total_papers": data["total_count"],
                "accepted_papers": data["accepted_count"],
                "acceptance_rate": f"{data['acceptance_rate']:.2%}"
            }
            for year, data in historical_data.items()
        },
        "prediction_method": "rule_based_with_historical_ranking"
    }


@app.get("/stats")
async def get_stats():
    """获取系统统计信息"""
    try:
        # 统计支付记录
        total_orders = len(payments)
        successful_payments = sum(1 for p in payments.values() if p["status"] == "success")
        total_revenue = sum(p["amount"] for p in payments.values() if p["status"] == "success")

        # 今日统计
        today = datetime.now().date()
        today_orders = sum(1 for p in payments.values()
                           if datetime.fromisoformat(p["created_at"]).date() == today)
        today_revenue = sum(p["amount"] for p in payments.values()
                            if p["status"] == "success" and
                            datetime.fromisoformat(p["created_at"]).date() == today)

        return {
            "total_orders": total_orders,
            "successful_payments": successful_payments,
            "total_revenue": total_revenue,
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "success_rate": successful_payments / total_orders if total_orders > 0 else 0,
            "prediction_stats": prediction_stats,
            "prediction_method": "rule_based_only",
            "historical_data": {  # 修复：添加历史数据信息
                year: {
                    "total_papers": data["total_count"],
                    "accepted_papers": data["accepted_count"],
                    "acceptance_rate": data["acceptance_rate"]
                }
                for year, data in historical_data.items()
            }
        }
    except Exception as e:
        return {"error": f"获取统计失败: {str(e)}"}


# 修复3：添加健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "data_loaded": len(historical_data) > 0,
        "historical_years": list(historical_data.keys())
    }


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 8000))

    print("🚀 启动论文接受率预测API...")
    print("✨ 特性:")
    print("  - 基于规则的预测算法")
    print("  - 历史数据支持排名计算")
    print("  - 详细的调试日志")
    print("  - 修复了CORS和移动端适配")
    print("  - 可配置支付等待时间")
    print("")
    print("🌐 访问地址:")
    print(f"  API服务: http://0.0.0.0:{port}")
    print(f"  API文档: http://0.0.0.0:{port}/docs")
    print(f"  数据状态: http://0.0.0.0:{port}/data-status")
    print(f"  健康检查: http://0.0.0.0:{port}/health")
    print(f"  系统统计: http://0.0.0.0:{port}/stats")

    uvicorn.run(app, host="0.0.0.0", port=port)