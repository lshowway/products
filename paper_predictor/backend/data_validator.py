#!/usr/bin/env python3
"""
数据验证脚本
检查ICLR数据文件是否格式正确，能被系统正确读取

用法：python validate_data.py [数据文件路径]
"""

import json
import sys
import os

def validate_paper(paper, line_num):
    """验证单篇论文数据格式"""
    issues = []
    
    # 检查必需字段
    required_fields = ['paper_title', 'paper_decision', 'reviews']
    for field in required_fields:
        if field not in paper:
            issues.append(f"缺少必需字段: {field}")
    
    # 检查评审数据
    if 'reviews' in paper and isinstance(paper['reviews'], list):
        valid_reviews = 0
        for i, review in enumerate(paper['reviews']):
            if isinstance(review, dict):
                rating = review.get('rating', '')
                if rating and rating != '-1':
                    try:
                        score = float(rating)
                        if 1 <= score <= 10:
                            valid_reviews += 1
                    except:
                        pass
        
        if valid_reviews == 0:
            issues.append("没有有效的评审评分")
    else:
        issues.append("reviews字段格式错误或缺失")
    
    return issues

def validate_jsonl_file(file_path):
    """验证JSONL文件"""
    print(f"🔍 验证数据文件: {file_path}")
    print("=" * 50)
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    try:
        valid_papers = 0
        total_lines = 0
        issues_count = 0
        accepted_papers = 0
        all_scores = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                line = line.strip()
                
                if not line:
                    continue
                
                try:
                    paper = json.loads(line)
                    
                    # 验证论文格式
                    issues = validate_paper(paper, line_num)
                    
                    if not issues:
                        valid_papers += 1
                        
                        # 统计接受情况
                        decision = paper.get('paper_decision', '').lower()
                        if 'accept' in decision:
                            accepted_papers += 1
                        
                        # 收集评分
                        for review in paper.get('reviews', []):
                            rating = review.get('rating', '')
                            if rating and rating != '-1':
                                try:
                                    score = float(rating)
                                    if 1 <= score <= 10:
                                        all_scores.append(score)
                                except:
                                    pass
                    else:
                        issues_count += 1
                        if issues_count <= 5:  # 只显示前5个问题
                            print(f"⚠️  第{line_num}行问题: {'; '.join(issues)}")
                
                except json.JSONDecodeError as e:
                    issues_count += 1
                    if issues_count <= 5:
                        print(f"❌ 第{line_num}行JSON解析错误: {e}")
        
        print(f"\n📊 验证结果:")
        print(f"  - 总行数: {total_lines}")
        print(f"  - 有效论文: {valid_papers}")
        print(f"  - 问题论文: {issues_count}")
        print(f"  - 接受论文: {accepted_papers}")
        print(f"  - 接受率: {accepted_papers/valid_papers*100:.1f}%" if valid_papers > 0 else "  - 接受率: 无法计算")
        
        if all_scores:
            print(f"  - 有效评分数: {len(all_scores)}")
            print(f"  - 评分范围: {min(all_scores):.1f} - {max(all_scores):.1f}")
            print(f"  - 平均评分: {sum(all_scores)/len(all_scores):.2f}")
        
        if valid_papers > 0:
            print(f"\n✅ 数据文件格式正确，可以被系统使用！")
            
            if valid_papers < 100:
                print(f"⚠️  建议: 论文数量较少({valid_papers}篇)，ML模型效果可能有限")
            
            return True
        else:
            print(f"\n❌ 数据文件没有有效论文，无法使用")
            return False
            
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return False

def quick_fix_suggestions():
    """提供快速修复建议"""
    print(f"\n🔧 数据格式要求:")
    print(f"每行必须是一个完整的JSON对象，包含:")
    print(f"- paper_title: 论文标题")
    print(f"- paper_decision: 决策结果(包含'accept'或'reject')")
    print(f"- reviews: 评审列表，每个评审包含:")
    print(f"  - rating: 评分(1-10的数字)")
    print(f"  - confidence: 自信心(1-5的数字，可选)")
    print(f"\n💡 如果数据格式不正确，可以使用data_processor.py进行转换")

def main():
    if len(sys.argv) < 2:
        print("📖 使用方法:")
        print("  python validate_data.py <数据文件路径>")
        print("\n💡 示例:")
        print("  python validate_data.py nips_history_data/ICLR_2024_formatted.jsonl")
        print("  python validate_data.py example.json")
        return
    
    file_path = sys.argv[1]
    
    print("🎯 ICLR数据验证工具")
    print("=" * 50)
    
    is_valid = validate_jsonl_file(file_path)
    
    if not is_valid:
        quick_fix_suggestions()
        sys.exit(1)
    else:
        print(f"\n🚀 建议:")
        print(f"1. 将此文件复制到 nips_history_data/ 目录")
        print(f"2. 重启后端服务: python main_ml.py")
        print(f"3. 检查管理界面的历史数据状态")

if __name__ == "__main__":
    main()