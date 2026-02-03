"""
Elsevier/ScienceDirect API客户端

需要API Key，建议同时申请TDM License用于非商业研究。
API文档: https://api.elsevier.com/
"""
import re
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup

from .api_client import APIClient, APIError


class ElsevierAPIClient(APIClient):
    """
    Elsevier API客户端

    支持ScienceDirect、Scopus等Elsevier产品。
    """

    # Elsevier域名
    ELSEVIER_DOMAINS = {
        'sciencedirect.com',
        'elsevier.com',
        'sdet.org',
        'doi.org',  # DOI解析服务 - 会尝试提取DOI并判断是否是Elsevier
    }

    # Elsevier DOI前缀 (10.1016 是Elsevier的主要DOI前缀)
    ELSEVIER_DOI_PREFIXES = {
        '10.1016',  # Elsevier (主要)
        '10.1016/j',  # Elsevier期刊
        '10.1016/jbs',  # 特定期刊
    }

    # API端点
    SCIENCE_DIRECT_API = "https://api.elsevier.com/content/article"
    SCOPUS_API = "https://api.elsevier.com/content/abstract"

    def __init__(self, config: Dict):
        elsevier_config = config.get('elsavier', {})
        super().__init__(elsevier_config)
        self.api_key = elsevier_config.get('api_key', '')
        self.tdm_license = elsevier_config.get('tdm_license', '')
        self.inst_token = elsevier_config.get('inst_token', '')

        if self.api_key:
            self.session.params.update({
                'apiKey': self.api_key
            })
            if self.inst_token:
                self.session.params.update({
                    'insttoken': self.inst_token
                })

        # TDM License需要特殊的请求头
        if self.tdm_license:
            self.session.headers.update({
                'X-ELS-License': self.tdm_license
            })

    def can_handle(self, url: str) -> bool:
        """判断是否是Elsevier URL"""
        domain = urlparse(url).netloc.lower()

        # 检查域名
        if any(elsevier_domain in domain for elsevier_domain in self.ELSEVIER_DOMAINS):
            # 如果是doi.org，需要进一步检查DOI前缀
            if 'doi.org' in domain:
                identifier = self._extract_identifier(url)
                if identifier:
                    # 检查是否是Elsevier的DOI前缀
                    return any(identifier.startswith(prefix) for prefix in self.ELSEVIER_DOI_PREFIXES)
                return False
            return True

        return False

    async def get_article(self, url: str) -> Dict[str, str]:
        """获取文章内容"""
        if not self.api_key:
            return {
                'success': False,
                'content': '',
                'source': 'elsevier_api',
                'error': 'Elsevier API key未配置',
                'requires_api': True
            }

        try:
            # 提取DOI或PII
            identifier = self._extract_identifier(url)

            if not identifier:
                return {
                    'success': False,
                    'content': '',
                    'source': 'elsevier_api',
                    'error': '无法从URL提取文章标识符'
                }

            return await self._get_via_api(identifier)

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'source': 'elsevier_api',
                'error': f'Elsevier API失败: {str(e)}'
            }

    async def _get_via_api(self, identifier: str) -> Dict[str, str]:
        """
        通过Elsevier API获取

        正确的URL格式:
        - DOI: https://api.elsevier.com/content/article/doi/{doi}?apiKey={key}
        - PII: https://api.elsevier.com/content/article/pii/{pii}?apiKey={key}
        """
        # 判断是DOI还是PII
        if identifier.startswith('10.'):
            url = f"{self.SCIENCE_DIRECT_API}/doi/{identifier}"
        else:
            url = f"{self.SCIENCE_DIRECT_API}/pii/{identifier}"

        # 优先使用ScienceDirect API获取摘要
        try:
            params = {'httpAccept': 'application/json'}
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 404:
                # 尝试Scopus API
                return await self._get_via_scopus(identifier)

            if response.status_code == 401:
                return {
                    'success': False,
                    'content': '',
                    'source': 'elsevier_api',
                    'error': 'API认证失败 - 请检查API Key是否正确'
                }

            if response.status_code == 429:
                return {
                    'success': False,
                    'content': '',
                    'source': 'elsevier_api',
                    'error': 'API速率限制 - 请稍后重试'
                }

            response.raise_for_status()

            # Elsevier API返回JSON
            data = response.json()
            content = self._extract_abstract_from_response(data)

            if content:
                return {
                    'success': True,
                    'content': content,
                    'source': 'elsevier_api',
                    'api_name': 'Elsevier ScienceDirect API'
                }

            return {
                'success': False,
                'content': '',
                'source': 'elsevier_api',
                'error': 'API返回数据中未找到摘要'
            }

        except requests.RequestException as e:
            raise APIError(f'API请求失败: {str(e)}')

    async def _get_via_scopus(self, identifier: str) -> Dict[str, str]:
        """
        通过Scopus API获取

        正确的URL格式:
        - DOI: https://api.elsevier.com/content/abstract/doi/{doi}?apiKey={key}
        - PII: https://api.elsevier.com/content/abstract/pii/{pii}?apiKey={key}
        """
        try:
            # 构建URL（identifier在路径中）
            if identifier.startswith('10.'):
                url = f"{self.SCOPUS_API}/doi/{identifier}"
            else:
                url = f"{self.SCOPUS_API}/pii/{identifier}"

            params = {'httpAccept': 'application/json'}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            content = self._extract_abstract_from_scopus(data)

            if content:
                return {
                    'success': True,
                    'content': content,
                    'source': 'elsevier_api',
                    'api_name': 'Elsevier Scopus API'
                }

            return {
                'success': False,
                'content': '',
                'source': 'elsevier_api',
                'error': 'Scopus API返回数据中未找到摘要'
            }

        except requests.RequestException as e:
            raise APIError(f'Scopus API请求失败: {str(e)}')

    def _extract_identifier(self, url: str) -> Optional[str]:
        """
        从URL提取文章标识符

        ScienceDirect URL格式:
        - https://www.sciencedirect.com/science/article/pii/S000000000000000
        - https://doi.org/10.1016/j.ijmedinf.2022.104830
        - https://www.sciencedirect.com/science/article/abs/10.1016/j.xxx.yyy

        优先使用DOI，因为API对DOI的支持更好
        """
        # 优先尝试提取DOI（在路径或查询参数中）
        doi_match = re.search(r'10\.\d{4,9}/[^\s\?"<>#]+', url)
        if doi_match:
            return doi_match.group(0)

        # 尝试提取PII（从/pii/路径）
        # PII格式: 以字母开头，后跟字母数字组合，如 S0304405X26000085
        pii_match = re.search(r'/pii/([A-Z][A-Z0-9]+)', url)
        if pii_match:
            return pii_match.group(1)

        # 从路径提取PII
        path = urlparse(url).path
        parts = path.split('/')

        for part in parts:
            # PII格式: 字母开头 + 字母数字组合
            if re.match(r'^[A-Z][A-Z0-9]+$', part):
                return part

        return None

    def _extract_abstract_from_response(self, data: Dict) -> str:
        """从ScienceDirect API响应提取摘要"""
        try:
            # ScienceDirect API返回的JSON结构:
            # { "full-text-retrieval-response": { "coredata": {...}, "originalText": ... } }
            abstract = ""

            # 首先检查是否包装在full-text-retrieval-response中
            if 'full-text-retrieval-response' in data:
                response_data = data['full-text-retrieval-response']

                # 尝试不同的路径
                if 'coredata' in response_data and 'dc:description' in response_data['coredata']:
                    abstract = response_data['coredata']['dc:description']
                elif 'originalText' in response_data:
                    abstract = response_data['originalText']
                elif 'items' in response_data:
                    items = response_data['items']
                    if isinstance(items, list):
                        for item in items:
                            if 'description' in item:
                                desc = item['description']
                                if isinstance(desc, str) and len(desc) > 50:
                                    abstract = desc
                                    break
            else:
                # 尝试直接从data中提取
                if 'coredata' in data and 'dc:description' in data['coredata']:
                    abstract = data['coredata']['dc:description']
                elif 'originalText' in data:
                    abstract = data['originalText']
                elif 'items' in data:
                    items = data['items']
                    if isinstance(items, list):
                        for item in items:
                            if 'description' in item:
                                desc = item['description']
                                if isinstance(desc, str) and len(desc) > 50:
                                    abstract = desc
                                    break

            if isinstance(abstract, str):
                return abstract.strip()

            return ""

        except (KeyError, TypeError):
            return ""

    def _extract_abstract_from_scopus(self, data: Dict) -> str:
        """从Scopus API响应提取摘要"""
        try:
            # Scopus API返回的JSON结构
            if 'abstracts-retrieval-response' in data:
                response_data = data['abstracts-retrieval-response']

                # 摘要在item中
                if 'item' in response_data:
                    items = response_data['item']

                    # 可能是单个item或数组
                    if isinstance(items, dict):
                        items = [items]

                    for item in items:
                        if 'description' in item:
                            desc = item['description']
                            if isinstance(desc, str) and len(desc) > 50:
                                return desc.strip()

                        # 检查bibrecord
                        if 'bibrecord' in item:
                            bibrecord = item['bibrecord']
                            if 'head' in bibrecord:
                                head = bibrecord['head']
                                if 'abstracts' in head:
                                    abstracts = head['abstracts']
                                    if isinstance(abstracts, dict):
                                        abstracts = [abstracts]
                                    for abstract_block in abstracts:
                                        if 'abstract' in abstract_block:
                                            abstract_text = abstract_block['abstract']
                                            if isinstance(abstract_text, str):
                                                return abstract_text.strip()
                                            elif isinstance(abstract_text, dict) and '$' in abstract_text:
                                                return abstract_text['$'].strip()

            return ""

        except (KeyError, TypeError):
            return ""


# 测试
if __name__ == '__main__':
    import asyncio

    async def test():
        config = {
            'elsavier': {
                'enabled': True,
                'api_key': 'your_api_key_here',  # 替换为实际API key
                'tdm_license': '',
                'inst_token': ''
            }
        }

        client = ElsevierAPIClient(config)

        # 测试URL
        test_urls = [
            "https://www.sciencedirect.com/science/article/pii/S000000000000000",
        ]

        for url in test_urls:
            print(f"\n{'='*60}")
            print(f"测试: {url}")
            print(f"{'='*60}")

            result = await client.get_article(url)
            print(f"成功: {result['success']}")
            print(f"来源: {result.get('source', 'N/A')}")

            if result['success']:
                print(f"内容长度: {len(result['content'])} 字符")
                print(f"\n内容预览:\n{result['content'][:400]}...")
            else:
                print(f"错误: {result['error']}")

    asyncio.run(test())
