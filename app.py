# app.py - 完整可运行版本
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
import traceback
from datetime import datetime
import time

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 动态导入配置
try:
    from config.config import load_config, load_paths

    config_loaded = True
except ImportError:
    print("⚠️  config模块导入失败，使用默认配置")
    config_loaded = False

app = Flask(__name__)
CORS(app)

# 全局变量
config = None
paths_config = None
finder = None
voter = None
kg_client = None
kg_enhancer = None


def initialize_components():
    """初始化所有组件"""
    global config, paths_config, finder, voter, kg_client, kg_enhancer

    print("🚀 初始化药物靶点查找器...")

    try:
        # 加载配置
        if config_loaded:
            config = load_config('config/api_config.yaml')
            paths_config = load_paths('config/paths.yaml')
        else:
            # 使用默认配置
            config = {
                'zhipu': {
                    'ZHIPUAI_API_KEY': '3723c056af754a59aa2b89ddbf56a59b.oeiARjPAKi7ssKw4',
                    'base_url': 'https://open.bigmodel.cn/api/paas/v4/',
                    'model': 'glm-4.6',
                    'temperature': 0.1,
                    'max_tokens': 4000
                },
                'deepseek': {
                    'api_key': 'sk-9d622bd81987484f9cd8c7d79da08fc8',
                    'base_url': 'https://api.deepseek.com',
                    'model': 'deepseek-chat',
                    'temperature': 0.1,
                    'max_tokens': 2000
                },
                'pubmed': {
                    'base_url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils',
                    'email': 'csong5381@gmail.com',
                    'tool': 'drug_target_atlas',
                    'rate_limit': 3,
                    'max_results': 10
                }
            }
            paths_config = {
                'data': {'output_dir': 'data/output'},
                'logs': {
                    'main': 'logs/main.log',
                    'pubmed': 'logs/pubmed.log',
                    'llm': 'logs/llm.log'
                }
            }

        # 动态导入模块
        from src.drug_target_finder import DrugTargetFinder
        from src.multi_model_voter import MultiModelVoter
        from src.knowledge_graph_client import KnowledgeGraphClient
        from src.kg_enhancer import KnowledgeGraphEnhancer

        # 初始化组件
        finder = DrugTargetFinder(config, paths_config)
        voter = MultiModelVoter(config)
        kg_client = KnowledgeGraphClient(config)
        kg_enhancer = KnowledgeGraphEnhancer()

        print("✅ 所有组件初始化完成")
        return True

    except Exception as e:
        print(f"❌ 组件初始化失败: {e}")
        traceback.print_exc()
        return False


# 在启动时初始化
if not initialize_components():
    print("⚠️ 组件初始化失败，某些功能可能不可用")


def filter_results(results, filters):
    """根据筛选条件过滤结果"""
    if not results:
        return []

    filtered = []

    for target in results:
        # 置信度筛选
        if 'confidence_levels' in filters:
            if target.get('confidence_level') not in filters['confidence_levels']:
                continue

        # 年份筛选
        if 'year_range' in filters:
            start_year, end_year = filters['year_range']
            try:
                target_year = int(target.get('year', 0))
                if target_year < start_year or target_year > end_year:
                    continue
            except:
                continue

        # 机制类型筛选
        if 'mechanism_type' in filters and filters['mechanism_type'] != 'All':
            mechanism = target.get('mechanism', '').lower()
            mechanism_type = filters['mechanism_type'].lower()

            keyword_map = {
                'inhibitor': ['inhibit', 'inhibition', 'block', 'antagonist', 'suppress'],
                'agonist': ['agonize', 'activate', 'stimulate', 'potentiate'],
                'antagonist': ['antagonize', 'block', 'inhibit', 'neutralize'],
                'modulator': ['modulate', 'regulate', 'modify', 'alter'],
                'activator': ['activate', 'stimulate', 'induce', 'promote'],
                'suppressor': ['suppress', 'inhibit', 'downregulate', 'repress']
            }

            if mechanism_type in keyword_map:
                keywords = keyword_map[mechanism_type]
                if not any(keyword in mechanism for keyword in keywords):
                    continue

        filtered.append(target)

    return filtered


@app.route('/')
def serve_ui():
    """提供UI页面"""
    return send_from_directory('.', 'ui.html')


@app.route('/api/health')
def health_check():
    """健康检查端点"""
    components_status = {
        'config_loaded': config is not None,
        'paths_loaded': paths_config is not None,
        'finder_initialized': finder is not None,
        'voter_initialized': voter is not None,
        'kg_client_initialized': kg_client is not None,
        'kg_enhancer_initialized': kg_enhancer is not None
    }

    status = 'healthy' if all(components_status.values()) else 'degraded'

    return jsonify({
        'status': status,
        'message': 'DrugTarget Explorer Service',
        'components': components_status,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/standard_search', methods=['POST'])
def standard_search():
    """标准搜索API - 使用GLM单模型分析"""
    try:
        data = request.json
        drug_name = data.get('drug_name', '').strip()
        filters = data.get('filters', {})

        if not drug_name:
            return jsonify({'error': 'Please enter drug name'}), 400

        print(f"🔍 标准搜索药物: {drug_name}")

        if finder is None:
            return jsonify({'error': 'Drug target finder not initialized'}), 500

        # 执行搜索和分析
        targets = finder.find_drug_targets(drug_name)

        # 应用筛选
        if filters:
            targets = filter_results(targets, filters)

        # 格式化结果
        formatted_results = []
        for target in targets:
            formatted_target = {
                'target_name': target.get('target_name', 'Unknown target'),
                'target_type': target.get('target_type', 'Protein'),
                'mechanism': target.get('mechanism', ''),
                'confidence_level': target.get('confidence_level', 'medium'),
                'confidence_display': get_confidence_display(target.get('confidence_level')),
                'pubmed_id': target.get('pubmed_id', ''),
                'evidence': target.get('evidence', ''),
                'year': target.get('year', 'Unknown'),
                'title': target.get('title', ''),
                'source': 'PubMed + GLM-4.6'
            }

            if formatted_target['pubmed_id']:
                formatted_target['pubmed_url'] = f"https://pubmed.ncbi.nlm.nih.gov/{formatted_target['pubmed_id']}/"

            formatted_results.append(formatted_target)

        # 按置信度排序
        confidence_order = {'high': 3, 'medium': 2, 'low': 1}
        formatted_results.sort(key=lambda x: confidence_order.get(x.get('confidence_level', 'low'), 1), reverse=True)

        response_data = {
            'status': 'success',
            'search_mode': 'standard',
            'drug_name': drug_name,
            'results': formatted_results,
            'summary': {
                'total_targets': len(formatted_results),
                'high_confidence': len([t for t in formatted_results if t.get('confidence_level') == 'high']),
                'medium_confidence': len([t for t in formatted_results if t.get('confidence_level') == 'medium']),
                'low_confidence': len([t for t in formatted_results if t.get('confidence_level') == 'low'])
            },
            'filters_applied': filters
        }

        print(f"✅ 标准搜索完成: 找到 {len(formatted_results)} 个靶点")
        return jsonify(response_data)

    except Exception as e:
        error_msg = f'Standard search failed: {str(e)}'
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@app.route('/api/advanced_search', methods=['POST'])
def advanced_search():
    """高级搜索API - 使用双模型投票系统"""
    try:
        data = request.json
        drug_name = data.get('drug_name', '').strip()
        filters = data.get('filters', {})

        if not drug_name:
            return jsonify({'error': 'Please enter drug name'}), 400

        print(f"🚀 启动高级搜索: {drug_name}")
        start_time = time.time()

        # 检查组件是否初始化
        if finder is None or voter is None or kg_enhancer is None:
            return jsonify({'error': 'System components not initialized'}), 500

        # 检查模型可用性
        voter_status = voter.get_system_status()
        if not voter_status.get('models_ready'):
            return jsonify({
                'status': 'error',
                'message': 'Both AI models must be configured with valid API keys',
                'details': voter_status
            }), 400

        # 1. 获取先验知识
        print(f"   🧠 获取药物先验知识: {drug_name}")
        drug_info = kg_enhancer.get_drug_info(drug_name)
        print(f"   ✅ 先验知识: {len(drug_info.get('known_targets', []))} 个已知靶点")

        # 2. 使用智能搜索获取文献
        print(f"   🔍 智能搜索药物: {drug_name}")
        articles = finder.pubmed_client.smart_search_drug_articles(drug_name, max_results=12)

        if not articles:
            return jsonify({'error': f'No literature found for drug "{drug_name}"'}), 404

        print(f"   ✅ 找到 {len(articles)} 篇相关文献")

        # 3. 分析文献的语言分布
        language_stats = {}
        for article in articles:
            lang = article.get('language', 'unknown')
            language_stats[lang] = language_stats.get(lang, 0) + 1

        print(f"   🌐 文献语言分布: {language_stats}")

        # 4. 选择要分析的文章
        english_articles = [a for a in articles if a.get('language') == 'english']
        mixed_articles = [a for a in articles if a.get('language') == 'mixed']
        other_articles = [a for a in articles if a.get('language') not in ['english', 'mixed']]

        # 构建分析列表
        articles_to_analyze = []
        articles_to_analyze.extend(english_articles[:8])

        if len(articles_to_analyze) < 5 and mixed_articles:
            needed = 5 - len(articles_to_analyze)
            additional = min(needed, len(mixed_articles))
            articles_to_analyze.extend(mixed_articles[:additional])

        if len(articles_to_analyze) < 3 and other_articles:
            articles_to_analyze.extend(other_articles[:2])

        print(f"   📄 选择 {len(articles_to_analyze)} 篇文章进行双模型分析")

        if len(articles_to_analyze) == 0:
            return jsonify({
                'status': 'info',
                'message': 'No suitable articles found for analysis',
                'suggestion': 'Try a different drug name or search strategy'
            }), 200

        # 5. 双模型分析
        print(f"   🤖 开始双模型分析...")
        all_analysis_results = []
        successful_analyses = 0

        for i, article in enumerate(articles_to_analyze, 1):
            print(f"      📄 分析文献 {i}/{len(articles_to_analyze)}")
            print(f"         标题: {article.get('title', 'No title')[:80]}...")
            print(f"         语言: {article.get('language', 'unknown')}")
            print(f"         年份: {article.get('year', 'Unknown')}")

            try:
                # 双模型分析单篇文章
                article_id = f"ART{i:03d}"
                result = voter.analyze_single_article(drug_name, article, article_id)

                if result.get('error'):
                    print(f"          ❌ 分析失败: {result.get('error')}")
                    continue

                # 检查是否有有效结果
                voting_result = result.get('voting_result', {})
                final_targets = voting_result.get('final_targets', [])

                if not final_targets:
                    print(f"          ⚠️  未找到靶点关系")
                    continue

                # 保存成功的分析结果
                analysis_result = {
                    'article_index': i,
                    'article_title': article.get('title', 'No title'),
                    'pubmed_id': article.get('pubmed_id', ''),
                    'year': article.get('year', 'Unknown'),
                    'analysis_result': result,
                    'targets_found': len(final_targets),
                    'article_language': article.get('language', 'unknown')
                }
                all_analysis_results.append(analysis_result)
                successful_analyses += 1

                print(f"          ✅ 提取到 {len(final_targets)} 个靶点")

                # API调用延迟
                if i < len(articles_to_analyze):
                    time.sleep(1.2)

            except Exception as e:
                print(f"          ❌ 文献分析异常: {str(e)[:50]}")
                continue

        # 6. 合并所有靶点
        all_targets = []
        total_deepseek_targets = 0
        total_glm_targets = 0
        total_consensus_targets = 0
        total_agreement = 0

        # 收集每个模型的详细靶点信息
        deepseek_target_names = []
        glm_target_names = []

        for analysis in all_analysis_results:
            result = analysis['analysis_result']
            voting_result = result.get('voting_result', {})
            final_targets = voting_result.get('final_targets', [])

            # 统计信息
            deepseek_targets = result.get('deepseek_targets', [])
            glm_targets = result.get('glm_targets', [])

            total_deepseek_targets += len(deepseek_targets)
            total_glm_targets += len(glm_targets)

            # 收集靶点名称
            for target in deepseek_targets:
                if target.get('target_name'):
                    deepseek_target_names.append(target['target_name'])
            for target in glm_targets:
                if target.get('target_name'):
                    glm_target_names.append(target['target_name'])

            consensus_targets = voting_result.get('consensus_targets', [])
            total_consensus_targets += len(consensus_targets)

            # 计算一致度
            agreement_metrics = voting_result.get('agreement_metrics', {})
            agreement_rate = agreement_metrics.get('agreement_rate', 0)
            total_agreement += agreement_rate

            for target in final_targets:
                # 知识图谱验证
                target_name = target.get('target_name')
                if target_name and kg_client:
                    validation_result = kg_client.validate_target_with_external_sources(drug_name, target_name)
                    if validation_result.get('is_validated'):
                        target['kg_boost'] = True
                        target['external_validation'] = validation_result
                        if 'confidence_boost' in validation_result:
                            # 提升置信度
                            if target.get('confidence_level') == 'medium':
                                target['confidence_level'] = 'high'

                target_with_article = {
                    **target,
                    'pubmed_id': analysis['pubmed_id'],
                    'title': analysis['article_title'],
                    'year': analysis['year'],
                    'article_index': analysis['article_index'],
                    'article_language': analysis['article_language'],
                    'analysis_method': 'dual_model_voting',
                    'analysis_time': result.get('analysis_time', 0)
                }
                all_targets.append(target_with_article)

        # 7. 去重和排序
        unique_targets = []
        seen_targets = set()

        for target in all_targets:
            target_key = f"{target['target_name'].lower().strip()}_{target.get('mechanism', '')[:50]}"
            if target_key not in seen_targets:
                seen_targets.add(target_key)
                unique_targets.append(target)

        # 按置信度和投票数排序
        unique_targets.sort(key=lambda x: (
            x.get('vote_count', 0),
            {'high': 3, 'medium': 2, 'low': 1}.get(x.get('confidence_level', 'low'), 1)
        ), reverse=True)

        # 8. 应用筛选
        if filters:
            unique_targets = filter_results(unique_targets, filters)

        # 9. 计算最终统计
        total_time = time.time() - start_time

        # 平均一致度
        avg_agreement = round(total_agreement / len(all_analysis_results), 1) if all_analysis_results else 0

        # 置信度统计
        high_conf = len([t for t in unique_targets if t.get('confidence_level') == 'high'])
        medium_conf = len([t for t in unique_targets if t.get('confidence_level') == 'medium'])
        low_conf = len([t for t in unique_targets if t.get('confidence_level') == 'low'])

        # 10. 准备模型靶点详情
        deepseek_target_names = list(set(deepseek_target_names))
        glm_target_names = list(set(glm_target_names))
        consensus_target_names = list(set(deepseek_target_names) & set(glm_target_names))

        # 11. 准备响应数据
        response_data = {
            'status': 'success',
            'search_mode': 'advanced',
            'drug_name': drug_name,
            'processing_time': round(total_time, 1),
            'articles_retrieved': len(articles),
            'articles_analyzed': len(all_analysis_results),
            'language_distribution': language_stats,
            'drug_info': {
                'has_prior_knowledge': drug_info.get('has_prior_knowledge', False),
                'known_targets_count': len(drug_info.get('known_targets', []))
            },
            'results': unique_targets,
            'summary': {
                'total_targets': len(unique_targets),
                'high_confidence': high_conf,
                'medium_confidence': medium_conf,
                'low_confidence': low_conf,
                'articles_with_targets': successful_analyses,
                'total_articles_analyzed': len(articles_to_analyze)
            },
            'comparison_data': {
                'deepseek_targets': len(deepseek_target_names),
                'glm_targets': len(glm_target_names),
                'common_targets': len(consensus_target_names),
                'agreement_rate': avg_agreement,
                'final_targets': len(unique_targets),
                'unique_targets': len(seen_targets)
            },
            'model_targets_details': {
                'deepseek_targets': deepseek_target_names[:10],
                'glm_targets': glm_target_names[:10],
                'consensus_targets': consensus_target_names[:10]
            },
            'analysis_details': {
                'models_used': ['DeepSeek', 'GLM-4.6'],
                'search_strategy': 'smart_multi_strategy',
                'max_articles_analyzed': len(articles_to_analyze),
                'timestamp': datetime.now().isoformat()
            },
            'filters_applied': filters
        }

        print(f"✅ 高级搜索完成!")
        print(f"   分析文献: {len(all_analysis_results)} 篇")
        print(f"   唯一靶点: {len(unique_targets)} 个")
        print(f"   模型一致度: {avg_agreement}%")
        print(f"   总耗时: {total_time:.1f}秒")

        return jsonify(response_data)

    except Exception as e:
        error_msg = f'Advanced search failed: {str(e)}'
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


def get_confidence_display(confidence_level):
    """获取置信度显示文本"""
    confidence_map = {
        'high': '🔴 High Confidence',
        'medium': '🟡 Medium Confidence',
        'low': '⚪ Low Confidence'
    }
    return confidence_map.get(confidence_level, '🟡 Medium Confidence')


@app.route('/api/export', methods=['POST'])
def export_results():
    """导出搜索结果"""
    try:
        data = request.json
        results = data.get('results', [])
        drug_name = data.get('drug_name', '')
        search_mode = data.get('search_mode', 'standard')

        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        if search_mode == 'advanced':
            writer.writerow(['Target Name', 'Type', 'Mechanism', 'Confidence',
                             'Sources', 'Vote Count', 'Year', 'PubMed ID',
                             'Evidence (English)', 'Title', 'Analysis Method'])
        else:
            writer.writerow(['Target Name', 'Type', 'Mechanism', 'Confidence',
                             'Year', 'PubMed ID', 'Evidence', 'Title', 'Model'])

        # 写入数据
        for target in results:
            if search_mode == 'advanced':
                sources = target.get('sources', [])
                sources_str = ', '.join(sources) if sources else 'Unknown'

                writer.writerow([
                    target.get('target_name', ''),
                    target.get('target_type', ''),
                    target.get('mechanism', ''),
                    target.get('confidence_level', ''),
                    sources_str,
                    target.get('vote_count', 1),
                    target.get('year', ''),
                    target.get('pubmed_id', ''),
                    target.get('evidence', '')[:200],
                    target.get('title', '')[:100],
                    target.get('analysis_method', 'dual_model')
                ])
            else:
                writer.writerow([
                    target.get('target_name', ''),
                    target.get('target_type', ''),
                    target.get('mechanism', ''),
                    target.get('confidence_level', ''),
                    target.get('year', ''),
                    target.get('pubmed_id', ''),
                    target.get('evidence', '')[:200],
                    target.get('title', '')[:100],
                    target.get('source', 'GLM-4.6')
                ])

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{drug_name}_{search_mode}_targets_{timestamp}.csv"

        return jsonify({
            'status': 'success',
            'csv_content': output.getvalue(),
            'filename': filename
        })

    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


@app.route('/api/debug/search', methods=['POST'])
def debug_search():
    """调试搜索API - 返回模拟数据"""
    try:
        data = request.json
        drug_name = data.get('drug_name', '').strip()
        search_mode = data.get('search_mode', 'standard')

        if not drug_name:
            return jsonify({'error': 'Please enter drug name'}), 400

        print(f"🔍 [调试] 模拟{search_mode}搜索: {drug_name}")

        if search_mode == 'standard':
            mock_results = [
                {
                    'target_name': 'COX-1',
                    'target_type': 'Enzyme',
                    'mechanism': 'Irreversible cyclooxygenase-1 inhibitor',
                    'confidence_level': 'high',
                    'confidence_display': '🔴 High Confidence',
                    'pubmed_id': '12345678',
                    'evidence': 'Aspirin irreversibly inhibits cyclooxygenase-1 (COX-1) enzyme through acetylation of serine residue.',
                    'year': '2023',
                    'title': 'Aspirin targets cyclooxygenase enzymes for anti-inflammatory effects',
                    'source': 'PubMed + GLM-4.6',
                    'pubmed_url': 'https://pubmed.ncbi.nlm.nih.gov/12345678/'
                },
                {
                    'target_name': 'COX-2',
                    'target_type': 'Enzyme',
                    'mechanism': 'Reversible cyclooxygenase-2 inhibitor',
                    'confidence_level': 'medium',
                    'confidence_display': '🟡 Medium Confidence',
                    'pubmed_id': '12345679',
                    'evidence': 'Aspirin also exhibits inhibitory effects on COX-2, contributing to its anti-inflammatory properties.',
                    'year': '2022',
                    'title': 'Dual inhibition of COX isoforms by aspirin derivatives',
                    'source': 'PubMed + GLM-4.6',
                    'pubmed_url': 'https://pubmed.ncbi.nlm.nih.gov/12345679/'
                }
            ]

            response_data = {
                'status': 'success',
                'search_mode': search_mode,
                'drug_name': drug_name,
                'results': mock_results,
                'summary': {
                    'total_targets': len(mock_results),
                    'high_confidence': 1,
                    'medium_confidence': 1,
                    'low_confidence': 0,
                    'articles_analyzed': 3
                },
                'processing_time': 0.8
            }

        else:
            # 高级搜索的模拟数据
            mock_results = [
                {
                    'target_name': 'COX-1',
                    'target_type': 'Enzyme',
                    'mechanism': 'Irreversible cyclooxygenase-1 inhibitor',
                    'confidence_level': 'high',
                    'confidence_display': '🔴 High Confidence',
                    'pubmed_id': '12345678',
                    'evidence': 'Aspirin irreversibly inhibits cyclooxygenase-1 (COX-1) enzyme through acetylation of serine residue.',
                    'year': '2023',
                    'title': 'Aspirin targets cyclooxygenase enzymes for anti-inflammatory effects',
                    'sources': ['deepseek', 'glm'],
                    'vote_count': 2,
                    'kg_boost': True,
                    'analysis_method': 'dual_model_voting',
                    'pubmed_url': 'https://pubmed.ncbi.nlm.nih.gov/12345678/'
                },
                {
                    'target_name': 'COX-2',
                    'target_type': 'Enzyme',
                    'mechanism': 'Irreversible cyclooxygenase-2 inhibitor',
                    'confidence_level': 'high',
                    'confidence_display': '🔴 High Confidence',
                    'pubmed_id': '12345679',
                    'evidence': 'Aspirin also inhibits cyclooxygenase-2 (COX-2) enzyme, although with lower affinity compared to COX-1.',
                    'year': '2023',
                    'title': 'Dual inhibition of COX-1 and COX-2 by aspirin',
                    'sources': ['glm'],
                    'vote_count': 1,
                    'kg_boost': False,
                    'analysis_method': 'dual_model_voting',
                    'pubmed_url': 'https://pubmed.ncbi.nlm.nih.gov/12345679/'
                },
                {
                    'target_name': 'NF-κB',
                    'target_type': 'Transcription Factor',
                    'mechanism': 'NF-κB signaling pathway inhibitor',
                    'confidence_level': 'medium',
                    'confidence_display': '🟡 Medium Confidence',
                    'pubmed_id': '12345680',
                    'evidence': 'Aspirin has been shown to inhibit NF-κB activation, contributing to its anti-inflammatory effects.',
                    'year': '2022',
                    'title': 'Anti-inflammatory mechanisms of aspirin beyond COX inhibition',
                    'sources': ['deepseek'],
                    'vote_count': 1,
                    'kg_boost': True,
                    'analysis_method': 'dual_model_voting',
                    'pubmed_url': 'https://pubmed.ncbi.nlm.nih.gov/12345680/'
                }
            ]

            response_data = {
                'status': 'success',
                'search_mode': search_mode,
                'drug_name': drug_name,
                'results': mock_results,
                'summary': {
                    'total_targets': len(mock_results),
                    'high_confidence': 2,
                    'medium_confidence': 1,
                    'low_confidence': 0,
                    'articles_with_targets': 3,
                    'total_articles_analyzed': 5
                },
                'processing_time': 2.5,
                'articles_retrieved': 12,
                'articles_analyzed': 5,
                'language_distribution': {'english': 4, 'mixed': 1},
                'comparison_data': {
                    'deepseek_targets': 5,
                    'glm_targets': 4,
                    'common_targets': 3,
                    'agreement_rate': 66.7,
                    'final_targets': 3,
                    'unique_targets': 3
                },
                'model_targets_details': {
                    'deepseek_targets': ['COX-1', 'COX-2', 'NF-κB', 'PPAR-alpha', 'AMPK'],
                    'glm_targets': ['COX-1', 'COX-2', 'IKK-beta', 'mTOR', 'EGFR'],
                    'consensus_targets': ['COX-1', 'COX-2']
                },
                'drug_info': {
                    'has_prior_knowledge': True,
                    'known_targets_count': 5
                }
            }

        print(f"✅ [调试] 返回模拟数据: {len(mock_results)} 个靶点")
        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': f'Debug search failed: {str(e)}'}), 500


@app.route('/api/system_status', methods=['GET'])
def system_status():
    """获取系统状态"""
    components_status = {
        'config_loaded': config is not None,
        'paths_loaded': paths_config is not None,
        'finder_initialized': finder is not None,
        'voter_initialized': voter is not None,
        'kg_client_initialized': kg_client is not None,
        'kg_enhancer_initialized': kg_enhancer is not None
    }

    # 获取模型状态
    model_status = {}
    if voter:
        model_status = voter.get_system_status()

    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'components': components_status,
        'models': model_status,
        'endpoints': {
            'standard_search': '/api/standard_search',
            'advanced_search': '/api/advanced_search',
            'export': '/api/export',
            'debug': '/api/debug/search',
            'health': '/api/health',
            'system_status': '/api/system_status'
        }
    })


@app.route('/api/quick_info', methods=['POST'])
def quick_info():
    """快速药物信息"""
    try:
        data = request.json
        drug_name = data.get('drug_name', '').strip()

        if not drug_name:
            return jsonify({'error': 'Please enter drug name'}), 400

        if kg_enhancer is None:
            return jsonify({'error': 'Knowledge graph not initialized'}), 500

        drug_info = kg_enhancer.get_drug_info(drug_name)

        return jsonify({
            'status': 'success',
            'drug_name': drug_name,
            'info': drug_info
        })

    except Exception as e:
        return jsonify({'error': f'Quick info failed: {str(e)}'}), 500


if __name__ == '__main__':
    print("🌐 启动DrugTarget Explorer服务...")
    print("📱 访问地址: http://localhost:5000")
    print("💡 核心功能:")
    print("   1. 标准搜索: PubMed + GLM-4.6 单模型分析")
    print("   2. 高级搜索: 智能搜索 + 双模型投票系统")
    print("   3. 调试模式: 模拟数据测试")
    print("   4. 导出功能: CSV格式结果导出")
    print("\n🔄 如果组件初始化失败，请检查配置文件")
    app.run(debug=True, host='0.0.0.0', port=5000)