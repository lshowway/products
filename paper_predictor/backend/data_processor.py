#!/usr/bin/env python3
"""
真实数据预处理脚本
将你的真实ICLR数据转换为系统可用格式

使用方法：
1. 将你的 example.json (或其他原始数据文件) 放在项目目录
2. 运行: python data_processor.py example.json nips_history_data/ICLR_2024_formatted.jsonl
3. 重启后端服务即可使用真实数据
"""

import json
import os
import sys
from pathlib import Path


def process_review_data(raw_data_file, output_file):
    """
    处理真实评审数据

    Args:
        raw_data_file: 原始数据文件路径 (如 example.json)
        output_file: 输出文件路径 (如 ICLR_2024_formatted.jsonl)
    """

    print(f"🔄 处理数据文件: {raw_data_file}")

    # 确保输出目录存在
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    valid_papers = 0

    try:
        # 判断输入文件格式
        if raw_data_file.endswith('.jsonl'):
            # JSONL格式 - 每行一个JSON对象
            with open(raw_data_file, 'r', encoding='utf-8') as infile:
                papers = []
                for line in infile:
                    line = line.strip()
                    if line:
                        papers.append(json.loads(line))
        else:
            # 单个JSON文件
            with open(raw_data_file, 'r', encoding='utf-8') as infile:
                data = json.load(infile)
                # 如果是单个论文对象，包装成列表
                if isinstance(data, dict):
                    papers = [data]
                else:
                    papers = data

        print(f"📊 发现 {len(papers)} 篇论文")

        # 处理每篇论文
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for paper in papers:
                processed_paper = process_single_paper(paper)
                if processed_paper:
                    outfile.write(json.dumps(processed_paper, ensure_ascii=False) + '\n')
                    valid_papers += 1
                processed_count += 1

                # 显示进度
                if processed_count % 100 == 0:
                    print(f"⏳ 已处理 {processed_count}/{len(papers)} 篇论文...")

    except Exception as e:
        print(f"❌ 处理文件时出错: {e}")
        return False

    print(f"✅ 数据处理完成!")
    print(f"   - 总数据: {processed_count} 篇")
    print(f"   - 有效数据: {valid_papers} 篇")
    print(f"   - 输出文件: {output_file}")

    # 分析数据质量
    analyze_processed_data(output_file)

    return True


def process_single_paper(paper_data):
    """
    处理单篇论文数据

    Args:
        paper_data: 原始论文数据

    Returns:
        dict: 格式化后的论文数据，如果数据无效返回None
    """

    try:
        # 提取基本信息
        paper_title = paper_data.get('paper_title', 'Unknown Title')
        paper_authors = paper_data.get('paper_authors', [])
        paper_abstract = paper_data.get('paper_abstract', '')
        paper_keywords = paper_data.get('paper_keywords', [])
        paper_tldr = paper_data.get('paper_tldr', '')
        paper_track = paper_data.get('paper_track', 'general')
        paper_venue = paper_data.get('paper_venue', 'ICLR 2024')
        paper_decision = paper_data.get('paper_decision', 'Unknown')

        # 处理评审数据
        reviews = paper_data.get('reviews', [])
        processed_reviews = []

        for review in reviews:
            # 跳过无效评审
            if not review or not isinstance(review, dict):
                continue

            # 提取评分和自信心
            rating = review.get('rating', '-1')
            confidence = review.get('confidence', '-1')
            reviewer = review.get('reviewer', '')

            # 处理对话数据
            dialogue = review.get('dialogue', [])

            processed_review = {
                "reviewer": reviewer,
                "rating": str(rating),
                "confidence": str(confidence),
                "dialogue": dialogue
            }

            processed_reviews.append(processed_review)

        # 如果没有有效评审，跳过这篇论文
        if not processed_reviews:
            return None

        # 构建最终数据结构
        formatted_paper = {
            "paper_title": paper_title,
            "paper_authors": paper_authors if isinstance(paper_authors, list) else [str(paper_authors)],
            "paper_abstract": paper_abstract,
            "paper_keywords": paper_keywords if isinstance(paper_keywords, list) else [str(paper_keywords)],
            "paper_tldr": paper_tldr,
            "paper_track": paper_track,
            "paper_venue": paper_venue,
            "paper_decision": paper_decision,
            "reviews": processed_reviews
        }

        return formatted_paper

    except Exception as e:
        print(f"⚠️  处理论文时出错: {e}")
        return None


def analyze_processed_data(data_file):
    """
    分析处理后的数据质量
    """

    print(f"\n📈 数据质量分析: {data_file}")
    print("=" * 50)

    try:
        papers = []
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                papers.append(json.loads(line.strip()))

        if not papers:
            print("❌ 没有找到有效数据")
            return

        # 基本统计
        total_papers = len(papers)
        accepted_papers = sum(1 for p in papers if 'accept' in p.get('paper_decision', '').lower())
        rejected_papers = sum(1 for p in papers if 'reject' in p.get('paper_decision', '').lower())
        acceptance_rate = accepted_papers / total_papers if total_papers > 0 else 0

        print(f"📊 论文总数: {total_papers}")
        print(f"✅ 接收论文: {accepted_papers} ({acceptance_rate:.1%})")
        print(f"❌ 拒绝论文: {rejected_papers} ({(1 - acceptance_rate):.1%})")

        # 评审统计
        all_scores = []
        all_confidences = []
        review_counts = []

        for paper in papers:
            reviews = paper.get('reviews', [])
            review_counts.append(len(reviews))

            for review in reviews:
                rating = review.get('rating', '-1')
                confidence = review.get('confidence', '-1')

                if rating != '-1':
                    try:
                        score = float(rating)
                        if 1 <= score <= 10:
                            all_scores.append(score)
                    except:
                        pass

                if confidence != '-1':
                    try:
                        conf = float(confidence)
                        if 1 <= conf <= 5:
                            all_confidences.append(conf)
                    except:
                        pass

        print(f"\n📝 评审统计:")
        print(f"   - 平均评审数/论文: {sum(review_counts) / len(review_counts):.1f}")
        print(f"   - 有效评分数: {len(all_scores)}")
        print(f"   - 评分范围: {min(all_scores):.1f} - {max(all_scores):.1f}")
        print(f"   - 平均评分: {sum(all_scores) / len(all_scores):.2f}")

        if all_confidences:
            print(f"   - 有效自信心数: {len(all_confidences)}")
            print(f"   - 平均自信心: {sum(all_confidences) / len(all_confidences):.2f}")

        # 评分分布
        score_distribution = {}
        for score in all_scores:
            score_int = int(score)
            score_distribution[score_int] = score_distribution.get(score_int, 0) + 1

        print(f"\n📊 评分分布:")
        for score in sorted(score_distribution.keys()):
            count = score_distribution[score]
            percentage = count / len(all_scores) * 100
            print(f"   - 评分 {score}: {count} ({percentage:.1f}%)")

    except Exception as e:
        print(f"❌ 分析数据时出错: {e}")


def batch_process_files(input_dir, output_dir):
    """
    批量处理多个数据文件
    """

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        print(f"❌ 输入目录不存在: {input_dir}")
        return

    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)

    # 查找所有JSON/JSONL文件
    json_files = list(input_path.glob("*.json")) + list(input_path.glob("*.jsonl"))

    if not json_files:
        print(f"❌ 在 {input_dir} 中没有找到JSON文件")
        return

    print(f"🔍 发现 {len(json_files)} 个数据文件")

    for json_file in json_files:
        # 生成输出文件名
        output_file = output_path / f"{json_file.stem}_formatted.jsonl"

        print(f"\n{'=' * 60}")
        success = process_review_data(str(json_file), str(output_file))

        if not success:
            print(f"❌ 处理失败: {json_file}")


def main():
    """主函数"""

    print("🎯 ICLR论文数据预处理工具")
    print("=" * 50)

    # 检查命令行参数
    if len(sys.argv) < 2:
        print("📖 使用方法:")
        print("   单文件: python data_processor.py <input_file> [output_file]")
        print("   批量处理: python data_processor.py --batch <input_dir> [output_dir]")
        print("")
        print("💡 示例:")
        print("   python data_processor.py example.json ICLR_2024_formatted.jsonl")
        print("   python data_processor.py --batch raw_data/ nips_history_data/")
        return

    if sys.argv[1] == "--batch":
        # 批量处理模式
        if len(sys.argv) < 3:
            print("❌ 批量处理需要指定输入目录")
            return

        input_dir = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "nips_history_data"

        batch_process_files(input_dir, output_dir)

    else:
        # 单文件处理模式
        input_file = sys.argv[1]

        if not os.path.exists(input_file):
            print(f"❌ 输入文件不存在: {input_file}")
            return

        # 生成输出文件名
        if len(sys.argv) > 2:
            output_file = sys.argv[2]
        else:
            # 自动生成输出文件名
            base_name = Path(input_file).stem
            output_file = f"nips_history_data/{base_name}_formatted.jsonl"

        process_review_data(input_file, output_file)

    print(f"\n🎉 处理完成！")
    print(f"📁 输出文件已保存到指定位置")
    print(f"🚀 现在可以启动API服务器测试预测功能了！")


if __name__ == "__main__":
    main()