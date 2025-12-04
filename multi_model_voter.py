import json
import time
import re
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


class MultiModelVoter:
    def __init__(self, config: Dict):
        self.config = config
        self.deepseek_config = config.get('deepseek', {})
        self.glm_config = config.get('zhipu', {})

        self.deepseek_available = self._validate_api_key(self.deepseek_config.get('api_key', ''), 'DeepSeek')
        self.glm_available = self._validate_api_key(self.glm_config.get('ZHIPUAI_API_KEY', ''), 'GLM')

        print(f"🤖 双模型投票系统初始化:")
        print(f"   DeepSeek: {'✅ 可用' if self.deepseek_available else '❌ 未配置'}")
        print(f"   GLM-4.6: {'✅ 可用' if self.glm_available else '❌ 未配置'}")

    def _validate_api_key(self, api_key: str, model_name: str) -> bool:
        if not api_key:
            return False

        if '你的' in api_key or 'your_' in api_key.lower():
            print(f"   ⚠️  {model_name}: 使用默认密钥，请配置真实API密钥")
            return False

        return True

    def get_system_status(self) -> Dict:
        return {
            'deepseek_available': self.deepseek_available,
            'glm_available': self.glm_available,
            'models_ready': self.deepseek_available and self.glm_available
        }

    def analyze_single_article(self, drug_name: str, article: Dict, article_id: str) -> Dict:
        print(f"      🎯 双模型分析文章 {article_id}")

        start_time = time.time()

        article_title = article.get('title', 'No title')
        article_abstract = article.get('abstract', 'No abstract')
        article_year = article.get('year', 'Unknown')
        pubmed_id = article.get('pubmed_id', '')

        print(f"         标题: {article_title[:60]}...")

        deepseek_response = None
        glm_response = None

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}

                if self.deepseek_available:
                    futures['deepseek'] = executor.submit(
                        self._call_deepseek_api, drug_name, article_title, article_abstract, article_year, pubmed_id,
                        article_id
                    )

                if self.glm_available:
                    futures['glm'] = executor.submit(
                        self._call_glm_api, drug_name, article_title, article_abstract, article_year, pubmed_id,
                        article_id
                    )

                for model, future in futures.items():
                    try:
                        response = future.result(timeout=45)
                        if model == 'deepseek':
                            deepseek_response = response
                            print(f"         ✅ DeepSeek 分析完成")
                        elif model == 'glm':
                            glm_response = response
                            print(f"         ✅ GLM-4.6 分析完成")
                    except Exception as e:
                        print(f"         ❌ {model} 分析失败: {str(e)[:50]}")

        except Exception as e:
            print(f"         ❌ 并行分析失败: {e}")
            return {'error': f'Analysis failed: {str(e)[:50]}'}

        analysis_time = time.time() - start_time

        deepseek_targets = self._extract_targets_from_response(deepseek_response,
                                                               'deepseek') if deepseek_response else []
        glm_targets = self._extract_targets_from_response(glm_response, 'glm') if glm_response else []

        print(f"         📊 DeepSeek: {len(deepseek_targets)} 个靶点, GLM: {len(glm_targets)} 个靶点")

        voting_result = self._perform_voting(deepseek_targets, glm_targets, drug_name)

        return {
            'article_id': article_id,
            'analysis_time': round(analysis_time, 2),
            'deepseek_targets': deepseek_targets,
            'glm_targets': glm_targets,
            'voting_result': voting_result,
            'deepseek_success': deepseek_response is not None,
            'glm_success': glm_response is not None
        }

    def _call_deepseek_api(self, drug_name: str, title: str, abstract: str, year: str, pubmed_id: str,
                           article_id: str) -> Optional[Dict]:
        try:
            api_key = self.deepseek_config.get('api_key')

            prompt = self._build_analysis_prompt(drug_name, title, abstract, year, pubmed_id, article_id)

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': self.deepseek_config.get('model', 'deepseek-chat'),
                'messages': [
                    {
                        'role': 'system',
                        'content': '''You are a professional biomedical research assistant. Extract drug-target relationships from medical literature. 
                        IMPORTANT: Evidence must be in ENGLISH, directly quoted from the abstract.
                        Output must be valid JSON format.'''
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': self.deepseek_config.get('temperature', 0.1),
                'max_tokens': self.deepseek_config.get('max_tokens', 2000),
                'response_format': {'type': 'json_object'}
            }

            response = requests.post(
                f"{self.deepseek_config.get('base_url', 'https://api.deepseek.com')}/chat/completions",
                headers=headers,
                json=data,
                timeout=40
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"         📄 DeepSeek 响应长度: {len(content)} 字符")
                return {
                    'content': content,
                    'status': 'success',
                    'model': 'deepseek-chat'
                }
            else:
                print(f"         ❌ DeepSeek API错误: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            print(f"         ⏱️  DeepSeek API调用超时")
            return None
        except Exception as e:
            print(f"         ❌ DeepSeek调用失败: {str(e)[:50]}")
            return None

    def _call_glm_api(self, drug_name: str, title: str, abstract: str, year: str, pubmed_id: str, article_id: str) -> \
    Optional[Dict]:
        try:
            api_key = self.glm_config.get('ZHIPUAI_API_KEY')

            prompt = self._build_analysis_prompt(drug_name, title, abstract, year, pubmed_id, article_id)

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': self.glm_config.get('model', 'glm-4'),
                'messages': [
                    {
                        'role': 'system',
                        'content': '''You are a professional biomedical research assistant. Extract drug-target relationships from medical literature. 
                        IMPORTANT: Evidence must be in ENGLISH, directly quoted from the abstract.
                        Output must be valid JSON format.'''
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': self.glm_config.get('temperature', 0.1),
                'max_tokens': self.glm_config.get('max_tokens', 4000)
            }

            response = requests.post(
                f"{self.glm_config.get('base_url', 'https://open.bigmodel.cn/api/paas/v4/')}chat/completions",
                headers=headers,
                json=data,
                timeout=40
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"         📄 GLM 响应长度: {len(content)} 字符")
                return {
                    'content': content,
                    'status': 'success',
                    'model': 'glm-4'
                }
            else:
                print(f"         ❌ GLM API错误: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            print(f"         ⏱️  GLM API调用超时")
            return None
        except Exception as e:
            print(f"         ❌ GLM调用失败: {str(e)[:50]}")
            return None

    def _build_analysis_prompt(self, drug_name: str, title: str, abstract: str, year: str, pubmed_id: str,
                               article_id: str) -> str:
        if len(abstract) > 3000:
            abstract = abstract[:3000] + "... [Abstract truncated]"

        abstract = abstract.replace('\n', ' ').replace('\r', ' ').strip()

        return f'''Extract drug-target relationships from the following medical literature:

DRUG: {drug_name}
ARTICLE ID: {article_id}
TITLE: {title}
PUBMED ID: {pubmed_id}
YEAR: {year}
ABSTRACT: {abstract}

CRITICAL INSTRUCTIONS:
1. Extract ONLY relationships EXPLICITLY mentioned in the abstract
2. Evidence MUST be DIRECT QUOTES from the abstract in ENGLISH
3. Do NOT infer or assume relationships
4. Output must be valid JSON format
5. For each target, provide the exact sentence from the abstract as evidence

CONFIDENCE LEVEL CRITERIA:
- high: The relationship is explicitly stated with clear evidence (e.g., "inhibits", "binds to", "targets")
- medium: The relationship is suggested or implied (e.g., "associated with", "involved in")
- low: Weak association mentioned

OUTPUT FORMAT (JSON):
{{
    "drug_name": "{drug_name}",
    "article_id": "{article_id}",
    "targets": [
        {{
            "target_name": "Specific target name (e.g., COX-1, EGFR, mTOR)",
            "target_type": "Enzyme/Receptor/Ion Channel/Transcription Factor/etc",
            "evidence": "Exact quote from abstract in English",
            "confidence_level": "high/medium/low",
            "mechanism": "Mechanism described in abstract (e.g., inhibits, activates, binds)"
        }}
    ]
}}

If NO drug-target relationship is found in the abstract, return:
{{
    "drug_name": "{drug_name}",
    "article_id": "{article_id}",
    "targets": []
}}

Now analyze the article and output valid JSON:'''

    def _extract_targets_from_response(self, response: Optional[Dict], model: str) -> List[Dict]:
        if not response or response.get('status') != 'success':
            return []

        try:
            content = response.get('content', '')
            if not content:
                return []

            content = content.strip()

            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                    except:
                        print(f"         ⚠️  {model} JSON解析失败")
                        return []
                else:
                    print(f"         ⚠️  {model} 未找到JSON")
                    return []

            targets = data.get('targets', [])
            if not isinstance(targets, list):
                return []

            formatted_targets = []
            for target in targets:
                if not isinstance(target, dict):
                    continue

                target_name = target.get('target_name', '').strip()
                evidence = target.get('evidence', '').strip()

                if not target_name or not evidence:
                    continue

                if not self._is_english(evidence):
                    print(f"         ⚠️  {model} 靶点 '{target_name}' 证据非英文")
                    continue

                confidence = target.get('confidence_level', 'medium').lower()
                if confidence not in ['high', 'medium', 'low']:
                    confidence = 'medium'

                formatted_target = {
                    'target_name': target_name,
                    'target_type': target.get('target_type', 'Protein'),
                    'confidence_level': confidence,
                    'evidence': evidence[:500],
                    'mechanism': target.get('mechanism', ''),
                    'source_model': model
                }

                formatted_targets.append(formatted_target)

            return formatted_targets

        except Exception as e:
            print(f"         ⚠️  {model} 靶点提取失败: {str(e)[:50]}")
            return []

    def _is_english(self, text: str) -> bool:
        if not text:
            return False

        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')

        if chinese_chars > len(text) * 0.3:
            return False

        return True

    def _perform_voting(self, deepseek_targets: List[Dict], glm_targets: List[Dict], drug_name: str) -> Dict:
        def normalize_target_name(name):
            name = name.lower().strip()
            name = name.replace('cyclooxygenase', 'cox')
            name = name.replace('nuclear factor kappa b', 'nf-κb')
            name = name.replace('amp-activated protein kinase', 'ampk')
            return name

        deepseek_names = {normalize_target_name(t['target_name']) for t in deepseek_targets}
        glm_names = {normalize_target_name(t['target_name']) for t in glm_targets}

        intersection = deepseek_names.intersection(glm_names)
        union = deepseek_names.union(glm_names)

        jaccard_similarity = len(intersection) / len(union) if union else 0
        agreement_rate = round(jaccard_similarity * 100, 1)

        print(
            f"         ⚖️ 投票统计: DeepSeek {len(deepseek_names)} | GLM {len(glm_names)} | 共识 {len(intersection)} | 一致度 {agreement_rate}%")

        all_targets_dict = {}

        for target in deepseek_targets:
            norm_name = normalize_target_name(target['target_name'])
            if norm_name not in all_targets_dict:
                all_targets_dict[norm_name] = {
                    'original_name': target['target_name'],
                    'sources': ['deepseek'],
                    'deepseek_data': target,
                    'vote_count': 1
                }

        for target in glm_targets:
            norm_name = normalize_target_name(target['target_name'])
            if norm_name in all_targets_dict:
                all_targets_dict[norm_name]['sources'].append('glm')
                all_targets_dict[norm_name]['vote_count'] = 2
                all_targets_dict[norm_name]['glm_data'] = target
            else:
                all_targets_dict[norm_name] = {
                    'original_name': target['target_name'],
                    'sources': ['glm'],
                    'glm_data': target,
                    'vote_count': 1
                }

        final_targets = []
        consensus_targets = []

        for norm_name, data in all_targets_dict.items():
            vote_count = data['vote_count']

            if vote_count == 2:
                confidence = 'high'
                decision = 'both_models_agree'
                consensus_targets.append(data['original_name'])

                deepseek_data = data.get('deepseek_data', {})
                glm_data = data.get('glm_data', {})

                evidence_parts = []
                if deepseek_data.get('evidence'):
                    evidence_parts.append(f"DeepSeek evidence: {deepseek_data['evidence']}")
                if glm_data.get('evidence'):
                    evidence_parts.append(f"GLM evidence: {glm_data['evidence']}")

                evidence = " | ".join(evidence_parts) if evidence_parts else "Both models identified this target."
                mechanism = deepseek_data.get('mechanism') or glm_data.get('mechanism') or ''
                target_type = deepseek_data.get('target_type') or glm_data.get('target_type') or 'Protein'

            else:
                confidence = 'medium'
                decision = 'single_model'
                single_data = data.get('deepseek_data') or data.get('glm_data', {})
                evidence = single_data.get('evidence', '')
                mechanism = single_data.get('mechanism', '')
                target_type = single_data.get('target_type', 'Protein')

            if evidence and not self._is_english(evidence):
                evidence = "Evidence not available in English"

            final_target = {
                'target_name': data['original_name'],
                'target_type': target_type,
                'mechanism': mechanism[:200],
                'confidence_level': confidence,
                'evidence': evidence[:500],
                'sources': data['sources'],  # 重要：这里保存来源信息
                'vote_count': vote_count,
                'decision_reason': decision
            }

            final_targets.append(final_target)

        final_targets.sort(key=lambda x: (x['vote_count'],
                                          {'high': 3, 'medium': 2, 'low': 1}.get(x['confidence_level'], 1)),
                           reverse=True)

        return {
            'final_targets': final_targets,
            'consensus_targets': consensus_targets,
            'agreement_metrics': {
                'jaccard_similarity': round(jaccard_similarity, 3),
                'agreement_rate': agreement_rate,
                'deepseek_only': len(deepseek_names - glm_names),
                'glm_only': len(glm_names - deepseek_names),
                'both_agree': len(intersection),
                'total_unique': len(union)
            },
            'voting_stats': {
                'total_deepseek_targets': len(deepseek_targets),
                'total_glm_targets': len(glm_targets),
                'total_final_targets': len(final_targets),
                'consensus_targets_count': len(consensus_targets)
            }
        }