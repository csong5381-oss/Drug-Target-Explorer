"""
知识图谱增强模块 - 提供药物先验知识和检索优化
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class DrugInfo:
    """药物信息数据类"""
    name: str
    known_targets: List[str]
    mechanisms: List[str]
    pathways: List[str]
    synonyms: List[str]

class KnowledgeGraphEnhancer:
    """轻量级知识图谱增强系统"""

    def __init__(self):
        # 预定义常见药物知识库
        self.drug_knowledge_base = self._init_drug_knowledge()

    def _init_drug_knowledge(self) -> Dict[str, DrugInfo]:
        """初始化药物知识库"""
        return {
            'aspirin': DrugInfo(
                name='Aspirin',
                known_targets=['COX-1', 'COX-2', 'NF-κB', 'IKK-beta', 'PPAR-alpha'],
                mechanisms=[
                    'irreversible cyclooxygenase inhibitor',
                    'anti-inflammatory',
                    'antiplatelet agent',
                    'NF-κB pathway inhibitor'
                ],
                pathways=[
                    'Arachidonic acid metabolism',
                    'Inflammatory response pathway',
                    'NF-κB signaling pathway',
                    'Prostaglandin synthesis'
                ],
                synonyms=['Acetylsalicylic Acid', 'ASA', 'Aspirinum']
            ),
            'metformin': DrugInfo(
                name='Metformin',
                known_targets=['AMPK', 'mitochondrial complex I', 'mTOR', 'GLUT4'],
                mechanisms=[
                    'AMPK activator',
                    'insulin sensitizer',
                    'mitochondrial respiration inhibitor',
                    'mTOR inhibitor'
                ],
                pathways=[
                    'AMPK signaling pathway',
                    'Insulin signaling pathway',
                    'mTOR signaling pathway',
                    'Glucose metabolism'
                ],
                synonyms=['Glucophage', 'Dimethylbiguanide', 'Metformina']
            ),
            'ibuprofen': DrugInfo(
                name='Ibuprofen',
                known_targets=['COX-1', 'COX-2', 'PPAR-gamma'],
                mechanisms=[
                    'non-steroidal anti-inflammatory drug',
                    'reversible COX inhibitor',
                    'PPAR-gamma activator'
                ],
                pathways=[
                    'Prostaglandin biosynthesis',
                    'Inflammatory response',
                    'PPAR signaling pathway'
                ],
                synonyms=['Advil', 'Motrin', 'Brufen']
            ),
            'simvastatin': DrugInfo(
                name='Simvastatin',
                known_targets=['HMG-CoA reductase', 'LDL receptor', 'RhoA', 'eNOS'],
                mechanisms=[
                    'HMG-CoA reductase inhibitor',
                    'cholesterol-lowering agent',
                    'pleiotropic effects'
                ],
                pathways=[
                    'Cholesterol biosynthesis',
                    'Mevalonate pathway',
                    'Rho GTPase signaling'
                ],
                synonyms=['Zocor', 'Simvastatina', 'Liponorm']
            ),
            'atorvastatin': DrugInfo(
                name='Atorvastatin',
                known_targets=['HMG-CoA reductase', 'LDL receptor', 'VLDL receptor'],
                mechanisms=[
                    'HMG-CoA reductase inhibitor',
                    'cholesterol synthesis inhibitor'
                ],
                pathways=[
                    'Cholesterol biosynthesis',
                    'Lipid metabolism'
                ],
                synonyms=['Lipitor', 'Atorvastatina']
            )
        }

    def get_drug_info(self, drug_name: str) -> Dict:
        """获取药物完整信息"""
        drug_lower = drug_name.lower()

        # 检查精确匹配
        if drug_lower in self.drug_knowledge_base:
            drug_info = self.drug_knowledge_base[drug_lower]
            return {
                'name': drug_info.name,
                'known_targets': drug_info.known_targets,
                'mechanisms': drug_info.mechanisms,
                'pathways': drug_info.pathways,
                'synonyms': drug_info.synonyms,
                'has_prior_knowledge': True
            }

        # 检查同义词匹配
        for key, drug_info in self.drug_knowledge_base.items():
            if drug_lower in [s.lower() for s in drug_info.synonyms]:
                return {
                    'name': drug_info.name,
                    'known_targets': drug_info.known_targets,
                    'mechanisms': drug_info.mechanisms,
                    'pathways': drug_info.pathways,
                    'synonyms': drug_info.synonyms,
                    'has_prior_knowledge': True
                }

        # 返回默认信息
        return {
            'name': drug_name,
            'known_targets': [],
            'mechanisms': [],
            'pathways': [],
            'synonyms': [],
            'has_prior_knowledge': False
        }

    def generate_search_strategies(self, drug_name: str) -> List[Dict]:
        """生成优化的搜索策略"""
        drug_info = self.get_drug_info(drug_name)

        strategies = []

        # 策略1：直接靶点搜索（如果有先验知识）
        if drug_info['has_prior_knowledge'] and drug_info['known_targets']:
            for target in drug_info['known_targets'][:3]:  # 前3个靶点
                strategies.append({
                    'strategy_id': 'known_target',
                    'description': f'搜索已知靶点: {target}',
                    'search_term': f'({drug_name}[Title/Abstract]) AND ({target}[Title/Abstract])',
                    'confidence': 'high',
                    'priority': 1
                })

        # 策略2：机制搜索
        if drug_info['mechanisms']:
            for mechanism in drug_info['mechanisms'][:2]:
                strategies.append({
                    'strategy_id': 'mechanism',
                    'description': f'搜索作用机制: {mechanism}',
                    'search_term': f'{drug_name}[Title/Abstract] AND "{mechanism}"',
                    'confidence': 'medium',
                    'priority': 2
                })

        # 策略3：基础搜索（保底）
        strategies.append({
            'strategy_id': 'basic',
            'description': f'基础药物搜索: {drug_name}',
            'search_term': f'{drug_name}[Title/Abstract]',
            'confidence': 'low',
            'priority': 3
        })

        # 按优先级排序
        strategies.sort(key=lambda x: x['priority'])

        return strategies

    def validate_target(self, drug_name: str, target_name: str) -> Dict:
        """验证靶点是否合理"""
        drug_info = self.get_drug_info(drug_name)

        # 精确匹配检查
        if target_name in drug_info['known_targets']:
            return {
                'is_valid': True,
                'confidence_boost': 0.3,
                'validation_level': 'exact_match',
                'evidence': f'已知靶点：{target_name}',
                'suggestion': '高置信度靶点'
            }

        # 模糊匹配检查
        target_lower = target_name.lower()
        for known_target in drug_info['known_targets']:
            known_lower = known_target.lower()

            # 检查子串匹配
            if target_lower in known_lower or known_lower in target_lower:
                return {
                    'is_valid': True,
                    'confidence_boost': 0.15,
                    'validation_level': 'partial_match',
                    'evidence': f'与已知靶点相似：{known_target}',
                    'suggestion': '可能为同一靶点的不同名称'
                }

            # 检查缩写匹配
            if self._is_abbreviation_match(target_name, known_target):
                return {
                    'is_valid': True,
                    'confidence_boost': 0.2,
                    'validation_level': 'abbreviation_match',
                    'evidence': f'可能是{known_target}的缩写',
                    'suggestion': '需确认是否为同一靶点'
                }

        # 无匹配
        return {
            'is_valid': False,
            'confidence_boost': 0.0,
            'validation_level': 'no_match',
            'evidence': '未在知识图谱中找到相关信息',
            'suggestion': '可能是新发现的靶点'
        }

    def _is_abbreviation_match(self, target1: str, target2: str) -> bool:
        """检查是否为缩写匹配"""
        common_abbr = {
            'COX': 'Cyclooxygenase',
            'EGFR': 'Epidermal Growth Factor Receptor',
            'VEGF': 'Vascular Endothelial Growth Factor',
            'NF-κB': 'Nuclear Factor Kappa B',
            'AMPK': 'AMP-activated Protein Kinase',
            'mTOR': 'mammalian Target Of Rapamycin',
            'HMG-CoA': '3-hydroxy-3-methylglutaryl-coenzyme A'
        }

        for abbr, full in common_abbr.items():
            if (target1 == abbr and full in target2) or (target2 == abbr and full in target1):
                return True
        return False

    def get_search_performance_metrics(self) -> Dict:
        """获取搜索性能指标（模拟）"""
        return {
            'total_strategies_generated': 25,
            'avg_strategies_per_drug': 4.2,
            'strategy_success_rate': '78%',
            'precision_improvement': '22%',
            'recall_improvement': '15%',
            'time_saved_per_search': '1.8s'
        }