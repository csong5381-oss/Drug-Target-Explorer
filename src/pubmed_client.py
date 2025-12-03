import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import time
import re
import os


class PubMedClient:
    def __init__(self, config: Dict, paths_config: Dict):
        self.base_url = config['pubmed']['base_url']
        self.email = config['pubmed']['email']
        self.tool = config['pubmed']['tool']
        self.max_results = config['pubmed']['max_results']
        self.rate_limit = config['pubmed']['rate_limit']
        self.paths_config = paths_config

    def search_drug_articles(self, drug_name: str, max_results: int = None) -> List[Dict]:
        """
        优化的药物文献搜索流程 - 优先搜索明确靶点的文章
        """
        if max_results is None:
            max_results = self.max_results

        print(f"🔍 搜索药物 '{drug_name}' 的靶点相关文献...")
        start_time = time.time()

        # 使用优化的搜索策略，优先靶点明确的结果
        article_ids = self._search_target_specific_articles(drug_name, max_results)

        if not article_ids:
            print(f"❌ 未找到药物 '{drug_name}' 的相关文献")
            return []

        print(f"📄 获取 {len(article_ids)} 篇文献的详细信息...")
        articles = self.get_article_details(article_ids)

        elapsed_time = time.time() - start_time
        print(f"✅ 成功获取 {len(articles)} 篇文献，耗时 {elapsed_time:.1f} 秒")

        return articles

    def _search_target_specific_articles(self, drug_name: str, max_results: int) -> List[str]:
        """
        优先搜索明确说明靶点的文章 - 优化速度版本
        """
        # 🔥 优化：减少搜索词数量，只保留最有效的
        search_terms = [
            # 最明确的靶点搜索
            f'{drug_name}[Title/Abstract] AND (target OR targets OR targeting)',
            f'{drug_name}[Title/Abstract] AND (binds to OR binding to OR binds)',
            f'{drug_name}[Title/Abstract] AND (inhibits OR inhibitor of OR inhibition)',

            # 备用搜索
            f'{drug_name}[Title/Abstract] AND (mechanism of action OR MOA)',
            f'{drug_name}[Title/Abstract]'
        ]

        all_article_ids = []

        print(f"   🎯 使用 {len(search_terms)} 个优化搜索词...")

        for i, search_term in enumerate(search_terms, 1):
            if len(all_article_ids) >= max_results:
                break

            try:
                params = {
                    'db': 'pubmed',
                    'term': search_term,
                    'retmode': 'json',
                    'retmax': min(8, max_results - len(all_article_ids)),  # 🔥 优化：减少每次请求数量
                    'sort': 'relevance',
                    'email': self.email,
                    'tool': self.tool
                }

                # 🔥 优化：减少超时时间
                response = requests.get(f"{self.base_url}/esearch.fcgi", params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                batch_ids = data.get('esearchresult', {}).get('idlist', [])

                if batch_ids:
                    # 添加新ID，避免重复
                    new_ids = [id for id in batch_ids if id not in all_article_ids]
                    all_article_ids.extend(new_ids)
                    print(f"     ✅ 搜索词 {i}: 找到 {len(new_ids)} 篇新文献")
                else:
                    print(f"     ⚠️  搜索词 {i}: 无结果")

            except Exception as e:
                print(f"     ❌ 搜索词 {i}: 失败 - {str(e)[:50]}")

            # 🔥 优化：减少请求间延迟
            if i < len(search_terms):
                time.sleep(0.3)  # 从0.5秒减少到0.3秒

        # 返回去重后的结果，限制数量
        unique_ids = list(set(all_article_ids))[:max_results]
        print(f"   📊 总计找到 {len(unique_ids)} 篇唯一文献")

        return unique_ids

    def get_article_details(self, article_ids: List[str]) -> List[Dict]:
        """
        获取文章详细信息
        """
        if not article_ids:
            return []

        # 限制每次获取的数量
        batch_ids = article_ids[:self.max_results]

        params = {
            'db': 'pubmed',
            'id': ','.join(batch_ids),
            'retmode': 'xml'
        }

        try:
            response = requests.get(f"{self.base_url}/efetch.fcgi", params=params, timeout=30)
            response.raise_for_status()

            articles = self._parse_articles_xml(response.content)
            print(f"   ✅ 成功解析 {len(articles)} 篇文献")
            return articles

        except Exception as e:
            print(f"   ❌ 获取文章详情错误: {e}")
            return []

    def _parse_articles_xml(self, xml_content: str) -> List[Dict]:
        """
        解析PubMed XML
        """
        try:
            root = ET.fromstring(xml_content)
            articles = []

            for article in root.findall('.//PubmedArticle'):
                article_info = self._parse_single_article(article)
                if article_info:
                    articles.append(article_info)

            return articles

        except Exception as e:
            print(f"   ❌ 解析文章XML错误: {e}")
            return []

    def _parse_single_article(self, article_element) -> Optional[Dict]:
        """
        解析单篇文章
        """
        try:
            # 提取标题
            title_element = article_element.find('.//ArticleTitle')
            title = title_element.text if title_element is not None else "No title"

            if not title or title == "No title":
                return None

            # 提取摘要
            abstract_texts = []
            for abstract_element in article_element.findall('.//AbstractText'):
                if abstract_element.text:
                    text = abstract_element.text.strip()
                    if text and text not in abstract_texts:
                        abstract_texts.append(text)

            abstract = " ".join(abstract_texts) if abstract_texts else "No abstract available"

            # 提取年份
            year = self._extract_year(article_element)

            # 提取PubMed ID
            pmid_element = article_element.find('.//PMID')
            pmid = pmid_element.text if pmid_element is not None else "Unknown"

            return {
                'pubmed_id': pmid,
                'title': title,
                'abstract': abstract,
                'year': year
            }

        except Exception as e:
            print(f"   ❌ 解析单篇文章XML错误: {e}")
            return None

    def _extract_year(self, article_element) -> str:
        """
        提取年份
        """
        pub_date_element = article_element.find('.//PubDate/Year')
        if pub_date_element is not None and pub_date_element.text:
            return pub_date_element.text

        medline_date = article_element.find('.//PubDate/MedlineDate')
        if medline_date is not None and medline_date.text:
            year_match = re.search(r'(\d{4})', medline_date.text)
            if year_match:
                return year_match.group(1)

        return "Unknown"