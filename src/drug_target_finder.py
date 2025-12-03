from typing import List, Dict


class DrugTargetFinder:
    def __init__(self, config: Dict, paths_config: Dict):
        self.config = config
        self.paths_config = paths_config

        from pubmed_client import PubMedClient
        from llm_processor import LLMProcessor

        self.pubmed_client = PubMedClient(config, paths_config)
        self.llm_processor = LLMProcessor(config)

    def find_drug_targets(self, drug_name: str) -> List[Dict]:
        """
        主要功能：输入药物名称，返回关联靶点列表
        """
        print(f"🎯 开始分析药物: {drug_name}")
        print(f"🚀 使用模型: {self.config['zhipu']['model']}")

        # 1. 从PubMed搜索相关文献
        articles = self.pubmed_client.search_drug_articles(drug_name)

        if not articles:
            print(f"❌ 未找到药物 '{drug_name}' 的相关文献")
            return []

        # 2. 使用大模型分析文献并提取靶点
        print(f"🤖 使用大模型分析 {len(articles)} 篇文献...")

        # 使用 batch_analyze_articles 方法
        analysis_results = self.llm_processor.batch_analyze_articles(
            drug_name, 1, articles
        )

        # 3. 提取所有靶点并标准化字段
        all_targets = []
        for result in analysis_results:
            if result and result.get('targets'):
                for target in result['targets']:
                    # 标准化靶点数据结构
                    standardized_target = {
                        'target_name': target.get('target_name', ''),
                        'target_type': target.get('target_type', '蛋白质'),  # 默认类型
                        'genes': target.get('genes', []),
                        'pathways': target.get('pathways', []),
                        'mechanism': target.get('mechanism', ''),
                        'evidence': target.get('reference', target.get('evidence', '')),
                        'confidence_level': target.get('confidence_level', 'medium'),
                        'pubmed_id': result.get('pubmed_id', ''),
                        'title': result.get('title', ''),
                        'year': result.get('year', '')
                    }
                    all_targets.append(standardized_target)

        # 4. 按置信度排序
        confidence_order = {'high': 3, 'medium': 2, 'low': 1}
        all_targets.sort(key=lambda x: confidence_order.get(x.get('confidence_level', 'low'), 1), reverse=True)

        # 5. 返回结果
        high_conf = len([t for t in all_targets if t.get('confidence_level') == 'high'])
        medium_conf = len([t for t in all_targets if t.get('confidence_level') == 'medium'])
        low_conf = len([t for t in all_targets if t.get('confidence_level') == 'low'])

        print(f"✅ 分析完成！找到 {len(all_targets)} 个靶点")
        print(f"📊 置信度分布: 高({high_conf}) 中({medium_conf}) 低({low_conf})")

        return all_targets