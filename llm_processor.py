import requests
import json
import re
from typing import List, Dict, Optional
import time
import numpy as np
import os
import csv
from datetime import datetime
import pandas as pd


class LLMProcessor:
    def __init__(self, config: Dict):
        self.api_key = config['zhipu']['ZHIPUAI_API_KEY']
        self.base_url = config['zhipu']['base_url']
        self.model = config['zhipu']['model']
        self.temperature = config['zhipu']['temperature']
        self.max_tokens = config['zhipu']['max_tokens']

        # 添加token统计
        self.token_usage_file = 'data/output/token_usage.csv'
        self._ensure_token_file()

    def _ensure_token_file(self):
        """确保token统计文件存在"""
        os.makedirs(os.path.dirname(self.token_usage_file), exist_ok=True)
        if not os.path.exists(self.token_usage_file):
            with open(self.token_usage_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'drug_name', 'article_id', 'prompt_tokens',
                                 'completion_tokens', 'total_tokens', 'cost_estimate'])

    def _record_token_usage(self, drug_name: str, article_id: str, response_data: Dict):
        """记录token使用情况"""
        try:
            usage = response_data.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            cost_estimate = (prompt_tokens * 0.1 / 1000) + (completion_tokens * 0.1 / 1000)

            with open(self.token_usage_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    drug_name,
                    article_id,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    round(cost_estimate, 4)
                ])

            print(
                f"💰 Token使用: 输入{prompt_tokens}, 输出{completion_tokens}, 总计{total_tokens}, 估算成本¥{cost_estimate:.4f}")

        except Exception as e:
            print(f"⚠️ 记录token使用失败: {e}")

    def analyze_article(self, drug_name: str, article: Dict, article_id: str) -> Optional[Dict]:
        """
        使用智谱AI分析单篇文章，提取药物-靶点关系
        """
        prompt = self._build_prompt(drug_name, article, article_id)

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': "你是一个专业的生物医学研究助手，专门从医学文献中提取药物-靶点关系信息。请根据证据强度设置置信等级，并确保输出是有效的JSON格式。"
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }

        try:
            print(f"发送请求到智谱AI API...")
            response = requests.post(
                f"{self.base_url}chat/completions",
                headers=headers,
                data=json.dumps(data, ensure_ascii=False),
                timeout=60
            )
            response.raise_for_status()

            result = response.json()

            self._record_token_usage(drug_name, article_id, result)

            content = result['choices'][0]['message']['content']

            print(f"LLM分析完成，响应长度: {len(content)} 字符")

            return self._parse_llm_response(content, article, article_id)

        except requests.exceptions.Timeout:
            print("智谱AI API调用超时")
            return None
        except Exception as e:
            print(f"智谱AI API调用错误: {e}")
            if hasattr(e, 'response'):
                print(f"响应内容: {e.response.text}")
            return None

    def _build_prompt(self, drug_name: str, article: Dict, article_id: str) -> str:
        """
        构建分析提示词
        """
        abstract = article['abstract']
        if len(abstract) > 3000:
            abstract = abstract[:3000] + "... [摘要被截断]"

        return f"""请从以下医学文献中精确提取药物-靶点关系信息：

药物名称：{drug_name}
文献编号：{article_id}
文献标题：{article['title']}
文献摘要：{abstract}
发表年份：{article['year']}
PubMed ID：{article['pubmed_id']}

请严格按照以下JSON格式输出：

{{
    "drug_name": "{drug_name}",
    "article_id": "{article_id}",
    "targets": [
        {{
            "target_name": "具体靶点蛋白名称",
            "genes": ["相关基因1", "相关基因2"],
            "pathways": ["相关信号通路1", "相关信号通路2"],
            "reference": "从摘要中直接复制支持该关系的具体句子",
            "confidence_level": "high/medium/low"
        }}
    ],
    "title": "{article['title']}",
    "year": "{article['year']}",
    "pubmed_id": "{article['pubmed_id']}"
}}

置信等级说明：
- high: 文献明确直接提到该靶点，有实验证据支持，如"inhibits", "binds to", "targets"等明确词汇
- medium: 文献间接提到或基于已知机制的推断，如"associated with", "involved in", "related to"等
- low: 基于相关性的推测，证据较弱，或需要进一步验证的关系

提取规则：
1. 每个明确提到的靶点单独一个对象，每个靶点占一行
2. 只提取文献中明确提到的信息，不要过度推断
3. 基因名称使用标准符号（如 STAT3, EGFR, TP53）
4. 靶点名称要具体明确（如 "cyclooxygenase-1" 而不是 "COX"）
5. 通路名称要完整（如 "PI3K/AKT signaling pathway"）
6. 引用句子必须来自原文摘要，直接复制原文
7. 根据证据强度合理设置置信等级
8. 如果没有找到关系，targets设为空数组[]
9. 确保输出是纯JSON格式，不要包含其他文本

重要：请仔细评估证据强度，合理设置置信等级！

现在请分析文献并输出JSON："""

    def _parse_llm_response(self, content: str, article: Dict, article_id: str) -> Optional[Dict]:
        """
        解析LLM的响应
        """
        try:
            print("开始解析LLM响应...")

            content = content.strip()
            print(f"原始响应长度: {len(content)}")

            json_content = self._extract_json(content)
            if not json_content:
                print("无法从响应中提取JSON内容")
                return None

            print(f"提取的JSON内容: {json_content[:100]}...")

            result = json.loads(json_content)

            result = self._validate_and_fix_fields(result, article, article_id)

            if self._has_valid_content(result):
                print(f"✅ 成功提取: {len(result['targets'])} 个靶点")
                confidence_counts = {}
                for target in result['targets']:
                    conf_level = target.get('confidence_level', 'medium')
                    confidence_counts[conf_level] = confidence_counts.get(conf_level, 0) + 1
                print(f"🎯 置信等级分布: {confidence_counts}")
                return result
            else:
                print("❌ 未提取到有效的靶点信息")
                return None

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            print(f"解析内容: {content[:200]}...")
            return None
        except Exception as e:
            print(f"❌ 处理LLM响应时发生错误: {e}")
            return None

    def _extract_json(self, content: str) -> Optional[str]:
        """从响应内容中提取JSON部分"""
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}'
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                extracted = matches[0].strip()
                if extracted.startswith('{') and extracted.endswith('}'):
                    print(f"使用模式找到JSON: {pattern}")
                    return extracted

        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1 and start < end:
                potential_json = content[start:end]
                json.loads(potential_json)
                print("直接提取JSON成功")
                return potential_json
        except:
            pass

        if content.startswith('{') and content.endswith('}'):
            print("使用整个内容作为JSON")
            return content

        return None

    def _validate_and_fix_fields(self, result: Dict, article: Dict, article_id: str) -> Dict:
        """验证和修复字段"""
        default_structure = {
            'drug_name': '',
            'article_id': article_id,
            'targets': [],
            'title': article['title'],
            'year': article['year'],
            'pubmed_id': article['pubmed_id']
        }

        for key, default_value in default_structure.items():
            if key not in result:
                result[key] = default_value
                print(f"添加缺失字段: {key} = {default_value}")

        result['drug_name'] = str(result.get('drug_name', ''))
        result['article_id'] = str(result.get('article_id', article_id))

        if not isinstance(result['targets'], list):
            result['targets'] = []

        valid_targets = []
        for target in result['targets']:
            if isinstance(target, dict) and target.get('target_name'):
                target.setdefault('genes', [])
                target.setdefault('pathways', [])
                target.setdefault('reference', '')
                target.setdefault('confidence_level', 'medium')

                if not isinstance(target['genes'], list):
                    if isinstance(target['genes'], str):
                        target['genes'] = [gene.strip() for gene in target['genes'].split(',') if gene.strip()]
                    else:
                        target['genes'] = []

                if not isinstance(target['pathways'], list):
                    if isinstance(target['pathways'], str):
                        target['pathways'] = [pathway.strip() for pathway in target['pathways'].split(',') if
                                              pathway.strip()]
                    else:
                        target['pathways'] = []

                if target['confidence_level'] not in ['high', 'medium', 'low']:
                    print(f"⚠️  无效的置信等级 '{target['confidence_level']}'，设置为默认值 'medium'")
                    target['confidence_level'] = 'medium'

                target['genes'] = [gene for gene in target['genes'] if gene and str(gene).strip()]
                target['pathways'] = [pathway for pathway in target['pathways'] if pathway and str(pathway).strip()]
                target['reference'] = str(target.get('reference', '')).strip()

                valid_targets.append(target)
                print(f"   ✅ 靶点 '{target['target_name']}' - 置信等级: {target['confidence_level']}")

        result['targets'] = valid_targets

        return result

    def _has_valid_content(self, result: Dict) -> bool:
        """检查是否有有效内容"""
        return len(result.get('targets', [])) > 0

    def batch_analyze_articles(self, drug_name: str, drug_index: int, articles: List[Dict]) -> List[Dict]:
        """
        批量分析多篇文章
        """
        results = []

        for i, article in enumerate(articles, 1):
            if article is None:
                print(f"⚠️  跳过第 {i} 篇文献：文章信息为空")
                continue

            article_id = f"D{drug_index:03d}.P{i:02d}"
            print(f"\n📖 分析第 {i}/{len(articles)} 篇文献 (编号: {article_id}):")
            print(f"   标题: {article['title'][:80]}...")
            print(f"   年份: {article['year']}")

            analysis_result = self.analyze_article(drug_name, article, article_id)

            if analysis_result:
                results.append(analysis_result)
                confidence_levels = [t.get('confidence_level', 'medium') for t in analysis_result['targets']]
                print(f"   ✅ 提取成功，找到 {len(analysis_result['targets'])} 个靶点")
                print(f"   🎯 置信等级: {dict(zip(*np.unique(confidence_levels, return_counts=True)))}")
            else:
                print(f"   ❌ 提取失败或无有效关系")

            time.sleep(1.5)

        print(f"\n🎯 药物 {drug_name} 分析完成: {len(results)}/{len(articles)} 篇文献提取到关系")

        if results:
            all_confidence = []
            for result in results:
                for target in result['targets']:
                    all_confidence.append(target.get('confidence_level', 'medium'))

            from collections import Counter
            confidence_stats = Counter(all_confidence)
            print(f"📊 总体置信等级分布: {dict(confidence_stats)}")

        return results