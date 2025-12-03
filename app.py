# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
import traceback

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from config.config import load_config, load_paths
from src.drug_target_finder import DrugTargetFinder

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化finder
print("🚀 初始化药物靶点查找器...")
config = load_config('config/api_config.yaml')
paths_config = load_paths('config/paths.yaml')
finder = DrugTargetFinder(config, paths_config)
print("✅ 药物靶点查找器初始化完成")


@app.route('/')
def serve_ui():
    """提供UI页面"""
    return send_from_directory('.', 'ui.html')


@app.route('/api/search', methods=['POST'])
def search_drug_targets():
    """药物靶点搜索API"""
    try:
        data = request.json
        drug_name = data.get('drug_name', '').strip()

        if not drug_name:
            return jsonify({'error': '请输入药物名称'}), 400

        print(f"🔍 开始搜索药物: {drug_name}")

        # 执行搜索和分析
        targets = finder.find_drug_targets(drug_name)

        # 格式化结果 - 确保所有字段都有值
        formatted_results = []
        for target in targets:
            formatted_target = {
                'target_name': target.get('target_name', '未知靶点'),
                'target_type': target.get('target_type', '蛋白质'),
                'mechanism': target.get('mechanism', target.get('evidence', '')),
                'confidence_level': target.get('confidence_level', 'medium'),
                'pubmed_id': target.get('pubmed_id', ''),
                'evidence': target.get('evidence', target.get('reference', '')),
                'year': target.get('year', '未知'),
                'title': target.get('title', '')
            }
            formatted_results.append(formatted_target)

        response_data = {
            'status': 'success',
            'drug_name': drug_name,
            'results': formatted_results,
            'summary': {
                'total_targets': len(targets),
                'high_confidence': len([t for t in targets if t.get('confidence_level') == 'high']),
                'medium_confidence': len([t for t in targets if t.get('confidence_level') == 'medium']),
                'low_confidence': len([t for t in targets if t.get('confidence_level') == 'low'])
            }
        }

        print(f"✅ 搜索完成: 找到 {len(targets)} 个靶点")
        return jsonify(response_data)

    except Exception as e:
        error_msg = f'搜索失败: {str(e)}'
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@app.route('/api/export', methods=['POST'])
def export_results():
    """导出搜索结果"""
    try:
        data = request.json
        results = data.get('results', [])
        drug_name = data.get('drug_name', '')

        # 生成CSV内容
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(['靶点名称', '靶点类型', '作用机制', '置信等级', 'PubMed ID', '年份', '文献标题'])

        # 写入数据
        for target in results:
            writer.writerow([
                target.get('target_name', ''),
                target.get('target_type', ''),
                target.get('mechanism', ''),
                target.get('confidence_level', ''),
                target.get('pubmed_id', ''),
                target.get('year', ''),
                target.get('title', '')
            ])

        return jsonify({
            'status': 'success',
            'csv_content': output.getvalue(),
            'filename': f"{drug_name}_targets.csv"
        })

    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500


@app.route('/api/health')
def health_check():
    """健康检查端点"""
    return jsonify({'status': 'healthy', 'message': '服务运行正常'})


@app.route('/api/debug/search', methods=['POST'])
def debug_search():
    """调试搜索API - 返回模拟数据用于测试"""
    try:
        data = request.json
        drug_name = data.get('drug_name', '').strip()

        if not drug_name:
            return jsonify({'error': '请输入药物名称'}), 400

        print(f"🔍 [调试] 模拟搜索药物: {drug_name}")

        # 返回模拟数据
        mock_results = [
            {
                'target_name': 'COX-1',
                'target_type': '酶',
                'mechanism': '不可逆抑制环氧化酶-1',
                'confidence_level': 'high',
                'pubmed_id': '12345678',
                'evidence': 'Aspirin irreversibly inhibits cyclooxygenase-1 (COX-1) enzyme',
                'year': '2023',
                'title': 'Aspirin targets cyclooxygenase enzymes for anti-inflammatory effects'
            },
            {
                'target_name': 'COX-2',
                'target_type': '酶',
                'mechanism': '不可逆抑制环氧化酶-2',
                'confidence_level': 'high',
                'pubmed_id': '12345679',
                'evidence': 'Aspirin also inhibits cyclooxygenase-2 (COX-2) enzyme',
                'year': '2023',
                'title': 'Aspirin targets cyclooxygenase enzymes for anti-inflammatory effects'
            },
            {
                'target_name': 'NF-κB',
                'target_type': '转录因子',
                'mechanism': '抑制NF-κB信号通路',
                'confidence_level': 'medium',
                'pubmed_id': '12345680',
                'evidence': 'Aspirin shows inhibitory effects on NF-κB signaling pathway',
                'year': '2022',
                'title': 'Anti-inflammatory mechanisms of aspirin beyond COX inhibition'
            }
        ]

        response_data = {
            'status': 'success',
            'drug_name': drug_name,
            'results': mock_results,
            'summary': {
                'total_targets': len(mock_results),
                'high_confidence': 2,
                'medium_confidence': 1,
                'low_confidence': 0
            }
        }

        print(f"✅ [调试] 返回模拟数据: {len(mock_results)} 个靶点")
        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': f'调试搜索失败: {str(e)}'}), 500


if __name__ == '__main__':
    print("🌐 启动DrugTarget Explorer服务...")
    print("📱 访问地址: http://localhost:5000")
    print("💡 调试模式: 使用 /api/debug/search 进行测试")
    app.run(debug=True, host='0.0.0.0', port=5000)