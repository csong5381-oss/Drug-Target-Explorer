import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple
import time
import re
import pandas as pd
import os


class PubMedClient:
    def __init__(self, config: Dict, paths_config: Dict):
        self.base_url = config['pubmed']['base_url']
        self.email = config['pubmed']['email']
        self.tool = config['pubmed']['tool']
        self.max_results = config['pubmed']['max_results']
        self.rate_limit = config['pubmed']['rate_limit']
        self.paths_config = paths_config

        # 药物类型关键词库
        self.drug_type_keywords = {
            'hormone': ['thyroid', 'estrogen', 'testosterone', 'cortisol', 'insulin',
                        'levothyroxine', 'hormone', 'steroid', 'glucocorticoid', 'progesterone'],
            'antibody': ['mab', 'izumab', 'umab', 'ximab', 'antibody', 'monoclonal'],
            'inhibitor': ['inib', 'ostat', 'prazole', 'tide', 'artan', 'olol', 'vastatin'],
            'antibiotic': ['mycin', 'cillin', 'floxacin', 'cycline', 'azole', 'penem'],
            'antiviral': ['vir', 'ciclovir', 'navir', 'previr', 'buvir', 'mivir'],
            'chemotherapy': ['platin', 'taxel', 'rubicin', 'citabine', 'mustine'],
            'biologic': ['cept', 'ercept', 'imumab', 'alimumab', 'cept'],
            'vaccine': ['vaccine', 'vax', 'ccine']
        }

    def smart_search_drug_articles(self, drug_name: str, max_results: int = None) -> List[Dict]:
        """
        智能药物文献搜索
        """
        if max_results is None:
            max_results = self.max_results

        print(f"🎯 启动智能搜索: {drug_name}")
        start_time = time.time()

        # 1. 检测药物类型
        drug_type, confidence = self._detect_drug_type_with_confidence(drug_name)
        print(f"   🧬 药物类型检测: {drug_type} (置信度: {confidence:.1%})")

        # 2. 生成优化的搜索策略
        search_strategies = self._generate_optimized_strategies(drug_name, drug_type, confidence)
        print(f"   📋 生成 {len(search_strategies)} 个搜索策略")

        # 3. 执行智能搜索
        all_article_ids = []
        successful_strategies = 0

        for i, (strategy_name, search_terms) in enumerate(search_strategies.items(), 1):
            print(f"   🎯 执行策略 {i}/{len(search_strategies)}: {strategy_name}")

            strategy_ids = self._execute_search_strategy_with_retry(
                drug_name, search_terms, max_results - len(all_article_ids)
            )

            if strategy_ids:
                new_ids = [id for id in strategy_ids if id not in all_article_ids]
                if new_ids:
                    all_article_ids.extend(new_ids)
                    successful_strategies += 1
                    print(f"   ✅ 策略成功: 找到 {len(new_ids)} 篇新文献")
                else:
                    print(f"   ⚠️  策略未找到新文献")
            else:
                print(f"   ❌ 策略失败")

            # 如果已达到目标，提前结束
            if len(set(all_article_ids)) >= max_results:
                print(f"   ⏹️  已达到目标文献数 ({max_results})，提前结束搜索")
                break

            # 策略间延迟
            if i < len(search_strategies):
                time.sleep(0.8)

        # 4. 获取文献详细信息
        unique_ids = list(set(all_article_ids))[:max_results]
        print(f"   📊 搜索完成: {successful_strategies}/{len(search_strategies)} 个策略成功")
        print(f"   🎯 总计找到 {len(unique_ids)} 篇唯一文献")

        if not unique_ids:
            print(f"❌ 未找到药物 '{drug_name}' 的相关文献")
            return []

        print(f"   📄 获取 {len(unique_ids)} 篇文献的详细信息...")
        articles = self.get_article_details(unique_ids)

        # 5. 增强文章信息
        enhanced_articles = []
        for article in articles:
            # 检测语言
            article['language'] = self._detect_language(article.get('abstract', ''))
            # 标记药物类型
            article['drug_type'] = drug_type
            enhanced_articles.append(article)

        # 6. 统计信息
        elapsed_time = time.time() - start_time
        language_stats = {}
        for article in enhanced_articles:
            lang = article['language']
            language_stats[lang] = language_stats.get(lang, 0) + 1

        print(f"   🌐 语言分布: {language_stats}")
        print(f"✅ 智能搜索完成: {len(enhanced_articles)} 篇文献，耗时 {elapsed_time:.1f} 秒")

        return enhanced_articles

    def _detect_drug_type_with_confidence(self, drug_name: str) -> Tuple[str, float]:
        """检测药物类型并返回置信度"""
        drug_lower = drug_name.lower()

        # 检查精确匹配
        for drug_type, keywords in self.drug_type_keywords.items():
            for keyword in keywords:
                if keyword in drug_lower or drug_lower in keyword:
                    # 计算置信度：完全匹配 > 部分匹配
                    if drug_lower == keyword:
                        return drug_type, 0.95
                    elif keyword in drug_lower:
                        return drug_type, 0.8
                    else:
                        return drug_type, 0.7

        # 检查后缀模式
        suffix_patterns = {
            'mab': ('antibody', 0.9),
            'inib': ('inhibitor', 0.85),
            'vir': ('antiviral', 0.8),
            'mycin': ('antibiotic', 0.85),
            'cillin': ('antibiotic', 0.85),
            'oxacin': ('antibiotic', 0.8),
            'vastatin': ('inhibitor', 0.8),
            'prazole': ('inhibitor', 0.75),
            'artan': ('inhibitor', 0.7),
            'olol': ('inhibitor', 0.7),
            'thasone': ('hormone', 0.8),
            'thyrine': ('hormone', 0.75)
        }

        for suffix, (drug_type, confidence) in suffix_patterns.items():
            if drug_lower.endswith(suffix):
                return drug_type, confidence

        # 默认类型
        return 'general', 0.5

    def _generate_optimized_strategies(self, drug_name: str, drug_type: str, confidence: float) -> Dict[str, List[str]]:
        """生成优化的搜索策略"""
        strategies = {}

        # 基础策略：高召回率
        strategies['基础搜索'] = [
            f'{drug_name}[Title/Abstract]',
            f'"{drug_name}"',
            f'{drug_name} AND review',
            f'{drug_name} AND clinical trial'
        ]

        # 基于药物类型的专门策略
        if drug_type != 'general' and confidence > 0.6:
            type_strategies = self._generate_type_specific_strategies(drug_name, drug_type)
            strategies.update(type_strategies)

        # 机制相关策略
        strategies['机制探索'] = [
            f'{drug_name} AND (mechanism OR target OR action)',
            f'{drug_name} AND (inhibits OR activates OR binds)',
            f'{drug_name} AND (receptor OR enzyme OR protein)',
            f'{drug_name} AND pathway'
        ]

        # 高级科学策略
        strategies['科学深度'] = [
            f'{drug_name} AND molecular',
            f'{drug_name} AND signaling',
            f'{drug_name} AND pharmacokinetics',
            f'{drug_name} AND pharmacodynamics',
            f'{drug_name} AND metabolism'
        ]

        # 安全性和应用策略
        strategies['临床应用'] = [
            f'{drug_name} AND therapeutic',
            f'{drug_name} AND efficacy',
            f'{drug_name} AND safety',
            f'{drug_name} AND treatment',
            f'{drug_name} AND therapy'
        ]

        return strategies

    def _generate_type_specific_strategies(self, drug_name: str, drug_type: str) -> Dict[str, List[str]]:
        """生成类型特定的搜索策略"""
        type_strategies = {}

        if drug_type == 'hormone':
            type_strategies['激素药物'] = [
                f'{drug_name} AND hormone replacement',
                f'{drug_name} AND receptor agonist',
                f'{drug_name} AND endocrine',
                f'{drug_name} AND physiological',
                f'{drug_name} AND (thyroid OR estrogen OR testosterone)'
            ]
        elif drug_type == 'antibody':
            type_strategies['抗体药物'] = [
                f'{drug_name} AND monoclonal antibody',
                f'{drug_name} AND immunotherapy',
                f'{drug_name} AND antigen',
                f'{drug_name} AND (binding OR blockade)',
                f'{drug_name} AND immune checkpoint'
            ]
        elif drug_type == 'inhibitor':
            type_strategies['抑制剂'] = [
                f'{drug_name} AND inhibitor',
                f'{drug_name} AND inhibition',
                f'{drug_name} AND (enzyme OR kinase)',
                f'{drug_name} AND (blocks OR suppresses)',
                f'{drug_name} AND molecular target'
            ]
        elif drug_type == 'antibiotic':
            type_strategies['抗生素'] = [
                f'{drug_name} AND antibiotic',
                f'{drug_name} AND antimicrobial',
                f'{drug_name} AND bacterial',
                f'{drug_name} AND (resistance OR susceptibility)',
                f'{drug_name} AND MIC'
            ]
        elif drug_type == 'antiviral':
            type_strategies['抗病毒'] = [
                f'{drug_name} AND antiviral',
                f'{drug_name} AND virus',
                f'{drug_name} AND (viral inhibition OR viral replication)',
                f'{drug_name} AND (HIV OR hepatitis OR influenza)'
            ]

        return type_strategies

    def _execute_search_strategy_with_retry(self, drug_name: str, search_terms: List[str],
                                            max_needed: int) -> List[str]:
        """执行搜索策略，带重试机制"""
        article_ids = []
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries and len(article_ids) < max_needed:
            if retry_count > 0:
                print(f"     🔄 重试 {retry_count}/{max_retries}")

            for i, search_term in enumerate(search_terms):
                if len(article_ids) >= max_needed:
                    break

                try:
                    # 根据重试次数调整参数
                    retry_delay = retry_count * 0.5
                    if retry_delay > 0:
                        time.sleep(retry_delay)

                    params = {
                        'db': 'pubmed',
                        'term': search_term,
                        'retmode': 'json',
                        'retmax': min(8, max_needed - len(article_ids)),
                        'sort': 'relevance',
                        'email': self.email,
                        'tool': self.tool
                    }

                    response = requests.get(f"{self.base_url}/esearch.fcgi", params=params, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    batch_ids = data.get('esearchresult', {}).get('idlist', [])

                    if batch_ids:
                        new_ids = [id for id in batch_ids if id not in article_ids]
                        if new_ids:
                            article_ids.extend(new_ids)
                            if retry_count == 0:
                                print(f"     ✅ 搜索词 {i + 1}: 找到 {len(new_ids)} 篇")
                            else:
                                print(f"     ✅ 重试成功: 搜索词 {i + 1}: 找到 {len(new_ids)} 篇")
                    else:
                        if retry_count == 0:
                            print(f"     ⚠️  搜索词 {i + 1}: 无结果")

                except requests.exceptions.Timeout:
                    print(f"     ⏰ 搜索词 {i + 1}: 超时")
                except requests.exceptions.ConnectionError:
                    print(f"     🌐 搜索词 {i + 1}: 连接错误")
                except Exception as e:
                    print(f"     ❌ 搜索词 {i + 1} 失败: {str(e)[:50]}")

                # 请求间延迟
                if i < len(search_terms) - 1:
                    time.sleep(0.2)

            # 如果找到足够文献，跳出重试循环
            if len(article_ids) >= max_needed:
                break

            retry_count += 1

        return article_ids

    def get_article_details(self, article_ids: List[str]) -> List[Dict]:
        """
        获取文章详细信息
        """
        if not article_ids:
            return []

        # 分批处理
        batch_size = min(5, len(article_ids))
        batches = [article_ids[i:i + batch_size] for i in range(0, len(article_ids), batch_size)]

        all_articles = []
        successful_batches = 0

        for i, batch in enumerate(batches):
            print(f"   📄 批次 {i + 1}/{len(batches)}: 获取 {len(batch)} 篇文献...")

            try:
                params = {
                    'db': 'pubmed',
                    'id': ','.join(batch),
                    'retmode': 'xml',
                    'retmax': len(batch)
                }

                response = requests.get(f"{self.base_url}/efetch.fcgi", params=params, timeout=30)
                response.raise_for_status()

                articles = self._parse_articles_xml(response.content)
                if articles:
                    all_articles.extend(articles)
                    successful_batches += 1
                    print(f"   ✅ 批次成功: 解析 {len(articles)} 篇文献")
                else:
                    print(f"   ⚠️  批次解析失败")

            except Exception as e:
                print(f"   ❌ 批次获取失败: {e}")

            # 批次间延迟
            if i < len(batches) - 1:
                time.sleep(1)

        print(f"   📊 批次处理完成: {successful_batches}/{len(batches)} 个批次成功")
        return all_articles

    def _parse_articles_xml(self, xml_content: str) -> List[Dict]:
        """
        解析PubMed XML
        """
        try:
            root = ET.fromstring(xml_content)
            articles = []
            parsed_count = 0
            error_count = 0

            for article in root.findall('.//PubmedArticle'):
                try:
                    article_info = self._parse_single_article(article)
                    if article_info:
                        articles.append(article_info)
                        parsed_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    continue

            print(f"   📝 XML解析统计: {parsed_count} 成功, {error_count} 失败")
            return articles

        except ET.ParseError as e:
            print(f"   ❌ XML解析错误: {e}")
            return []
        except Exception as e:
            print(f"   ❌ 解析文章XML时发生未知错误: {e}")
            return []

    def _parse_single_article(self, article_element) -> Optional[Dict]:
        """
        解析单篇文章
        """
        try:
            # 提取PubMed ID
            pmid_element = article_element.find('.//PMID')
            pmid = pmid_element.text if pmid_element is not None else "Unknown"
            if pmid == "Unknown":
                return None

            # 提取标题
            title_element = article_element.find('.//ArticleTitle')
            title = title_element.text if title_element is not None else "No title"
            if not title or title == "No title" or len(title.strip()) < 5:
                return None

            # 提取摘要
            abstract_texts = []
            abstract_elements = article_element.findall('.//AbstractText')

            if not abstract_elements:
                abstract_elements = article_element.findall('.//Abstract/AbstractText')

            for abstract_element in abstract_elements:
                if abstract_element is not None and abstract_element.text:
                    text = abstract_element.text.strip()
                    if text and text not in abstract_texts:
                        abstract_texts.append(text)

            abstract = " ".join(abstract_texts) if abstract_texts else "No abstract available"

            # 提取年份
            year = self._extract_year(article_element)

            # 提取期刊信息
            journal_element = article_element.find('.//Journal/Title')
            journal = journal_element.text if journal_element is not None else "Unknown"

            # 提取作者信息（前3位）
            authors = []
            author_elements = article_element.findall('.//AuthorList/Author')[:3]
            for author_elem in author_elements:
                last_name_elem = author_elem.find('LastName')
                fore_name_elem = author_elem.find('ForeName')
                if last_name_elem is not None and last_name_elem.text:
                    author_name = last_name_elem.text
                    if fore_name_elem is not None and fore_name_elem.text:
                        author_name += f" {fore_name_elem.text}"
                    authors.append(author_name)

            # 提取MeSH术语（关键词）
            mesh_terms = []
            mesh_elements = article_element.findall('.//MeshHeading/DescriptorName')[:5]
            for mesh_elem in mesh_elements:
                if mesh_elem is not None and mesh_elem.text:
                    mesh_terms.append(mesh_elem.text)

            return {
                'pubmed_id': pmid,
                'title': title,
                'abstract': abstract,
                'year': year,
                'journal': journal,
                'authors': authors[:3],
                'mesh_terms': mesh_terms[:5],
                'has_abstract': abstract != "No abstract available" and len(abstract) > 20
            }

        except Exception as e:
            return None

    def _extract_year(self, article_element) -> str:
        """
        增强的年份提取方法
        """
        # 尝试多种年份字段
        year_sources = [
            ('.//PubDate/Year', '标准年份'),
            ('.//ArticleDate/Year', '文章日期'),
            ('.//MedlineDate', 'Medline日期'),
            ('.//PubMedPubDate[@PubStatus="pubmed"]/Year', 'PubMed日期'),
            ('.//PubMedPubDate[@PubStatus="medline"]/Year', 'Medline索引日期')
        ]

        for xpath, source_name in year_sources:
            element = article_element.find(xpath)
            if element is not None and element.text:
                text = element.text.strip()
                if text:
                    year_match = re.search(r'(\d{4})', text)
                    if year_match:
                        year = year_match.group(1)
                        if 1800 <= int(year) <= 2100:
                            return year

        return "Unknown"

    def _is_english_abstract(self, text: str) -> bool:
        """
        优化的英文检测方法
        """
        if not text or len(text) < 20:
            return False

        # 1. 检测中文字符（严格排除）
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        if chinese_chars > 0:
            return False

        # 2. 检测非拉丁字母（宽松）
        latin_chars = sum(
            1 for char in text if ('\u0041' <= char <= '\u005a') or ('\u0061' <= char <= '\u007a') or char.isspace())
        latin_ratio = latin_chars / len(text) if len(text) > 0 else 0

        if latin_ratio < 0.6:
            return False

        # 3. 简单英文词汇检测
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
        if len(words) < 8:
            return False

        # 4. 常见的英文词汇（核心词汇）
        english_core_words = {'the', 'and', 'of', 'in', 'to', 'a', 'is', 'that', 'for', 'on', 'was', 'with', 'as', 'by',
                              'be'}

        words_lower = [w.lower() for w in words]
        english_count = sum(1 for word in words_lower if word in english_core_words)
        english_ratio = english_count / len(words) if len(words) > 0 else 0

        return english_ratio > 0.05

    def _detect_language(self, text: str) -> str:
        """
        检测文本语言
        """
        if not text:
            return 'unknown'

        # 检测中文字符
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        if chinese_chars > 0:
            chinese_ratio = chinese_chars / len(text)
            if chinese_ratio > 0.3:
                return 'chinese'
            else:
                return 'mixed'

        # 检测英文
        if self._is_english_abstract(text):
            return 'english'

        # 检测其他拉丁字母语言
        latin_chars = sum(1 for char in text if ('\u0041' <= char <= '\u005a') or ('\u0061' <= char <= '\u007a'))
        latin_ratio = latin_chars / len(text) if len(text) > 0 else 0

        if latin_ratio > 0.7:
            return 'latin_other'
        else:
            return 'other'

    def search_drug_articles(self, drug_name: str, max_results: int = None) -> List[Dict]:
        """兼容原有接口，调用智能搜索"""
        return self.smart_search_drug_articles(drug_name, max_results)