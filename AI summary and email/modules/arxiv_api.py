"""
arXiv API客户端

arXiv是完全免费的预印本服务器，无需注册即可访问所有内容。
API文档: https://arxiv.org/help/api/
"""
import re
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse

import requests


def parse_arxiv_response(element) -> str:
    """解析arXiv API响应中的摘要"""
    # 查找summary标签
    summary = element.find('{http://www.w3.org/2005/Atom}summary')
    if summary is not None and summary.text:
        return summary.text.strip()

    return ''


class ArXivAPIClient:
    """
    arXiv API客户端

    完全免费，无需API密钥。
    """

    # arXiv API端点
    BASE_URL = "http://export.arxiv.org/api/query"

    # arXiv域名
    ARXIV_DOMAINS = {
        'arxiv.org',
        'xxx.lanl.gov',  # arXiv旧域名
    }

    def __init__(self, config: Dict):
        arxiv_config = config.get('arxiv', {})
        self.enabled = arxiv_config.get('enabled', True)
        self.base_url = arxiv_config.get('base_url', self.BASE_URL)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; arXivAPI/1.0)',
        })

    def can_handle(self, url: str) -> bool:
        """判断是否是arXiv URL"""
        domain = urlparse(url).netloc.lower()
        return any(arxiv_domain in domain for arxiv_domain in self.ARXIV_DOMAINS)

    async def get_article(self, url: str) -> Dict[str, str]:
        """获取文章内容"""
        try:
            arxiv_id = self._extract_arxiv_id(url)

            if not arxiv_id:
                return {
                    'success': False,
                    'content': '',
                    'source': 'arxiv_api',
                    'error': '无法从URL提取arXiv ID'
                }

            return await self._get_by_id(arxiv_id)

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'source': 'arxiv_api',
                'error': f'arXiv API失败: {str(e)}'
            }

    async def _get_by_id(self, arxiv_id: str) -> Dict[str, str]:
        """通过arXiv ID获取文章"""
        try:
            params = {
                'id_list': arxiv_id,
            }

            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            # arXiv返回Atom XML格式
            content = self._parse_arxiv_xml(response.text)

            if content:
                return {
                    'success': True,
                    'content': content,
                    'source': 'arxiv_api',
                    'api_name': 'arXiv API'
                }

            return {
                'success': False,
                'content': '',
                'source': 'arxiv_api',
                'error': '未找到文章内容'
            }

        except requests.RequestException as e:
            return {
                'success': False,
                'content': '',
                'source': 'arxiv_api',
                'error': f'API请求失败: {str(e)}'
            }

    def _extract_arxiv_id(self, url: str) -> Optional[str]:
        """
        从URL提取arXiv ID

        支持的格式:
        - https://arxiv.org/abs/2301.12345
        - https://arxiv.org/pdf/2301.12345.pdf
        - arXiv:2301.12345
        """
        # 从URL路径提取
        parsed = urlparse(url)
        path = parsed.path

        # 匹配 /abs/ID 或 /pdf/ID
        match = re.search(r'/(abs|pdf)/(\d+\.\d+)', path)
        if match:
            return match.group(2)

        # 匹配 arXiv:ID 格式
        match = re.search(r'arxiv:(\d+\.\d+)', url, re.IGNORECASE)
        if match:
            return match.group(1)

        # 直接匹配ID格式
        match = re.search(r'\b(\d{4}\.\d+)\b', url)
        if match:
            return match.group(1)

        return None

    def _parse_arxiv_xml(self, xml_text: str) -> str:
        """解析arXiv API返回的XML"""
        try:
            import xml.etree.ElementTree as ET

            # 注册命名空间
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            root = ET.fromstring(xml_text)

            # 查找第一个entry
            entry = root.find('atom:entry', ns)

            if entry is None:
                return ''

            # 提取摘要
            summary = entry.find('atom:summary', ns)
            if summary is not None and summary.text:
                return summary.text.strip()

            return ''

        except Exception as e:
            # 回退到正则表达式提取
            return self._extract_abstract_fallback(xml_text)

    def _extract_abstract_fallback(self, xml_text: str) -> str:
        """使用正则表达式回退提取摘要"""
        # 尝试匹配<summary>标签内容
        match = re.search(r'<summary>([\s\S]*?)</summary>', xml_text)
        if match:
            abstract = match.group(1)
            # 移除HTML标签
            abstract = re.sub(r'<[^>]+>', '', abstract)
            return abstract.strip()

        return ''

    def get_article_by_id(self, arxiv_id: str) -> Dict[str, str]:
        """
        同步方法：通过arXiv ID获取文章

        Args:
            arxiv_id: arXiv文章ID，如 '2301.12345'

        Returns:
            Dict包含success, content, error等字段
        """
        import asyncio
        return asyncio.run(self._get_by_id(arxiv_id))


# 测试
if __name__ == '__main__':
    import asyncio

    async def test():
        config = {
            'arxiv': {
                'enabled': True,
                'base_url': 'http://export.arxiv.org/api/query'
            }
        }

        client = ArXivAPIClient(config)

        # 测试URL
        test_urls = [
            "https://arxiv.org/abs/2301.12345",  # 示例arXiv文章
            "https://arxiv.org/pdf/2301.07041.pdf",  # PDF版本
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
