# main.py
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.insert(0, project_root)

try:
    from config.config import load_config, load_paths
    from src.drug_target_finder import DrugTargetFinder
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("💡 请确保项目目录结构正确，并已安装所有依赖")
    sys.exit(1)


def save_results_to_json(drug_name: str, targets: list, output_dir: str):
    """将结果保存为JSON文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{drug_name.lower()}_targets_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    result_data = {
        "drug_name": drug_name,
        "analysis_time": datetime.now().isoformat(),
        "total_targets": len(targets),
        "targets": targets
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    print(f"💾 结果已保存到: {filepath}")
    return filepath


def display_targets_summary(targets: list):
    """显示靶点摘要信息"""
    if not targets:
        print("❌ 未找到任何靶点")
        return

    # 按置信度统计
    confidence_stats = {
        'high': 0,
        'medium': 0,
        'low': 0
    }

    target_types = {}

    for target in targets:
        conf_level = target.get('confidence_level', 'low')
        confidence_stats[conf_level] = confidence_stats.get(conf_level, 0) + 1

        # 使用安全的字段访问
        target_type = target.get('target_type', '蛋白质')  # 默认为蛋白质
        target_types[target_type] = target_types.get(target_type, 0) + 1

    print(f"\n📊 分析结果摘要:")
    print(f"   总靶点数: {len(targets)}")
    print(
        f"   置信度分布: 高({confidence_stats['high']}) 中({confidence_stats['medium']}) 低({confidence_stats['low']})")
    print(f"   靶点类型: {', '.join([f'{k}({v})' for k, v in target_types.items()])}")


def display_detailed_targets(targets: list):
    """显示详细的靶点信息"""
    print(f"\n🎯 详细靶点信息 ({len(targets)} 个):")
    print("=" * 80)

    for i, target in enumerate(targets, 1):
        confidence_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '⚪'
        }

        conf_level = target.get('confidence_level', 'low')
        conf_emoji = confidence_emoji.get(conf_level, '⚪')

        # 修复：使用安全的字段访问，提供默认值
        target_name = target.get('target_name', '未知靶点')
        target_type = target.get('target_type', '蛋白质')  # 默认为蛋白质

        print(f"\n{i}. {conf_emoji} {target_name} ({target_type})")
        print(f"   📍 置信度: {conf_level.upper()}")

        evidence = target.get('evidence', target.get('reference', ''))
        if evidence and len(evidence) > 120:
            evidence = evidence[:120] + "..."
        print(f"   📖 证据: {evidence}")

        mechanism = target.get('mechanism', '')
        if mechanism:
            print(f"   ⚗️  机制: {mechanism}")

        experimental = target.get('experimental_support', '')
        if experimental:
            print(f"   🔬 实验支持: {experimental}")

        print(f"   🆔 PMID: {target.get('pubmed_id', '未知')}")


def main():
    """主函数 - 药物靶点关联分析系统"""
    print("🎯 药物靶点关联分析系统")
    print("=" * 50)

    try:
        # 加载配置
        print("📁 加载配置文件...")
        config = load_config('config/api_config.yaml')
        paths_config = load_paths('config/paths.yaml')

        # 创建分析器实例
        print("🔧 初始化分析器...")
        finder = DrugTargetFinder(config, paths_config)

        print("✅ 系统初始化完成！")

        while True:
            print("\n" + "=" * 50)
            print("请选择操作:")
            print("1. 🔍 查找药物靶点")
            print("2. 📊 查看使用说明")
            print("3. ❌ 退出系统")
            print("=" * 50)

            choice = input("请输入选择 (1-3): ").strip()

            if choice == "1":
                drug_name = input("请输入药物英文名称: ").strip()
                if not drug_name:
                    print("❌ 药物名称不能为空")
                    continue

                print(f"\n🚀 开始分析药物: {drug_name}")
                print("⏳ 这可能需要几分钟时间，请耐心等待...")

                try:
                    # 执行分析
                    targets = finder.find_drug_targets(drug_name)

                    if targets:
                        # 显示摘要
                        display_targets_summary(targets)

                        # 显示详细信息
                        display_detailed_targets(targets)

                        # 保存结果
                        output_dir = paths_config['data']['output_dir']
                        saved_path = save_results_to_json(drug_name, targets, output_dir)

                        print(f"\n✅ 分析完成！结果已保存至: {saved_path}")

                        # 提供进一步操作选项
                        while True:
                            print("\n选择后续操作:")
                            print("a. 📋 重新显示结果")
                            print("b. 💾 导出详细信息")
                            print("c. 🔍 分析新药物")
                            print("d. 🏠 返回主菜单")

                            sub_choice = input("请选择 (a-d): ").strip().lower()

                            if sub_choice == 'a':
                                display_detailed_targets(targets)
                            elif sub_choice == 'b':
                                print("💾 导出功能开发中...")
                            elif sub_choice == 'c':
                                break
                            elif sub_choice == 'd':
                                break
                            else:
                                print("❌ 无效选择")

                    else:
                        print("❌ 未找到该药物的明确靶点")
                        print("💡 建议:")
                        print("   - 检查药物名称拼写")
                        print("   - 尝试使用通用名或化学名")
                        print("   - 该药物可能作用机制不明确")

                except Exception as e:
                    print(f"❌ 分析过程中出错: {e}")
                    import traceback
                    traceback.print_exc()

            elif choice == "2":
                print("\n📖 使用说明:")
                print("1. 输入药物英文名称（如: Aspirin, Metformin, Ibuprofen）")
                print("2. 系统会自动从PubMed搜索相关文献")
                print("3. 使用AI分析文献并提取药物靶点")
                print("4. 结果显示靶点名称、类型、置信度和证据")
                print("5. 结果会自动保存到 data/output 目录")
                print("\n💡 提示:")
                print("   - 使用准确的药物英文名称")
                print("   - 分析时间取决于文献数量")
                print("   - 高置信度结果更可靠")

            elif choice == "3":
                print("👋 感谢使用药物靶点分析系统！再见！")
                break

            else:
                print("❌ 无效选择，请重新输入")

    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，再见！")
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()


def batch_analysis():
    """批量分析函数（可选）"""
    drugs_to_analyze = ["Aspirin", "Metformin", "Ibuprofen"]

    config = load_config('config/api_config.yaml')
    paths_config = load_paths('config/paths.yaml')
    finder = DrugTargetFinder(config, paths_config)

    for drug in drugs_to_analyze:
        print(f"\n🔍 分析药物: {drug}")
        targets = finder.find_drug_targets(drug)

        if targets:
            display_targets_summary(targets)
            save_results_to_json(drug, targets, paths_config['data']['output_dir'])
        else:
            print(f"❌ 未找到 {drug} 的靶点")

        print("⏳ 等待10秒后继续下一个...")
        import time
        time.sleep(10)


if __name__ == "__main__":
    main()

    # 如果需要批量分析，取消注释下面的行
    # batch_analysis()