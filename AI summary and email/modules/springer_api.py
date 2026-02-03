"""
Springer Nature Open Access API客户端

Springer Nature提供完全免费的开放获取内容API，无需申请即可使用。
"""
import re
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .api_client import APIClient, APIError


class SpringerAPIClient(APIClient):
    """
    Springer Nature API客户端

    支持两种访问方式:
    1. Springer Metadata API - 需要API Key
    2. 直接爬取开放获取文章 - 无需API Key
    """

    # Springer域名
    SPRINGER_DOMAINS = {
        'springer.com',
        'springernature.com',
        'link.springer.com',
        'nature.com',
    }

    # API端点
    METADATA_API = "https://api.springernature.com/metadata/popen"

    def __init__(self, config: Dict):
        springer_config = config.get('springer', {})
        super().__init__(springer_config)
        self.api_key = springer_config.get('api_key', '')
        self.open_access_only = springer_config.get('open_access_only', True)

        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

    def can_handle(self, url: str) -> bool:
        """判断是否是Springer URL"""
        domain = urlparse(url).netloc.lower()
        return any(springer_domain in domain for springer_domain in self.SPRINGER_DOMAINS)

    async def get_article(self, url: str) -> Dict[str, str]:
        """获取文章内容"""
        try:
            # 如果有API key，尝试使用API
            if self.api_key and not self.open_access_only:
                return await self._get_via_api(url)

            # 否则尝试直接访问（仅开放获取）
            return await self._get_via_direct_access(url)

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'source': 'springer_api',
                'error': f'Springer API失败: {str(e)}'
            }

    async def _get_via_api(self, url: str) -> Dict[str, str]:
        """通过Springer Metadata API获取"""
        doi = self._extract_doi_from_url(url)

        if not doi:
            return {
                'success': False,
                'content': '',
                'source': 'springer_api',
                'error': '无法从URL提取DOI'
            }

        try:
            params = {'doi': doi}
            response = self.session.get(self.METADATA_API, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            content = self._extract_abstract_from_api(data)

            if content:
                return {
                    'success': True,
                    'content': content,
                    'source': 'springer_api',
                    'api_name': 'Springer Metadata API'
                }

            return {
                'success': False,
                'content': '',
                'source': 'springer_api',
                'error': 'API返回数据中未找到摘要'
            }

        except requests.RequestException as e:
            raise APIError(f'API请求失败: {str(e)}')

    async def _get_via_direct_access(self, url: str) -> Dict[str, str]:
        """直接访问Springer网站获取开放获取内容"""
        try:
            response = self.session.get(url, timeout=30, allow_redirects=True)

            if response.status_code == 403:
                return {
                    'success': False,
                    'content': '',
                    'source': 'springer_api',
                    'error': '访问被拒绝 - 可能需要订阅或API密钥',
                    'requires_api': True,
                    'suggestion': '考虑申请Springer API访问权限或使用开放获取文章'
                }

            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 尝试多种Springer摘要选择器
            abstract = self._extract_abstract_springer(soup)

            if abstract and len(abstract) > 50:
                return {
                    'success': True,
                    'content': abstract,
                    'source': 'springer_api',
                    'api_name': 'Springer Open Access'
                }

            return {
                'success': False,
                'content': '',
                'source': 'springer_api',
                'error': '未找到摘要内容 - 文章可能不是开放获取'
            }

        except requests.RequestException as e:
            return {
                'success': False,
                'content': '',
                'source': 'springer_api',
                'error': f'直接访问失败: {str(e)}'
            }

    def _extract_doi_from_url(self, url: str) -> Optional[str]:
        """从URL提取DOI"""
        # Springer URL中的DOI模式
        # 例如: https://link.springer.com/article/10.1007/s00148-021-00858-6
        patterns = [
            r'10\.\d{4,}/[^\s]+',  # 标准DOI
            r'article/([^/?]+)',  # /article/路径
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                doi = match.group(1) if match.lastindex else match.group(0)
                if doi.startswith('10.'):
                    return doi

        return None

    def _extract_abstract_from_api(self, data: Dict) -> str:
        """从API响应中提取摘要"""
        try:
            # Springer API返回的JSON结构
            records = data.get('records', [])

            if not records:
                return ''

            record = records[0]
            abstract = record.get('abstract', '')

            if abstract:
                return abstract.strip()

            # 尝试其他可能的字段
            for field in ['description', 'summary']:
                if field in record:
                    return record[field].strip()

            return ''

        except (KeyError, IndexError, TypeError):
            return ''

    def _extract_abstract_springer(self, soup: BeautifulSoup) -> str:
        """从Springer HTML页面提取摘要"""
        # Springer/LINK的摘要选择器
        selectors = [
            # Springer Nature
            '.Section1.Abstract p',
            '.Abstract p',
            '#abstract-content',
            '[data-test="abstract"]',

            # Nature
            '.c-article-section__content p',
            '.c-article-abstract p',

            # 通用
            'section[class*="abstract"] p',
            'div[class*="abstract"] p',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator=' ', strip=True)
                if len(text) > 50:
                    return text

        # 尝试从页面文本提取
        body_text = soup.get_text()
        abstract_match = re.search(
            r'Abstract\s+([\s\S]*?)(?=\n\s*(?:Keywords|Introduction|References|1\.))',
            body_text,
            re.IGNORECASE
        )

        if abstract_match:
            return abstract_match.group(1).strip()

        return ''


# 测试
if __name__ == '__main__':
    import asyncio

    async def test():
        config = {
            'springer': {
                'enabled': True,
                'api_key': '',
                'open_access_only': True
            }
        }

        client = SpringerAPIClient(config)

        # 测试URL
        test_urls = [
            "https://link.springer.com/article/10.1007/s00148-021-00858-6",  # 示例Springer文章
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
