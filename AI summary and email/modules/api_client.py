"""
官方API客户端基类

用于与学术出版商官方API通信，提供合法的内容获取方式。
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional
from urllib.parse import urlparse

import requests


class APIClient(ABC):
    """
    官方API客户端基类

    所有具体的API客户端应该继承此类并实现get_article方法。
    """

    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, application/xml, text/xml',
            'Accept-Encoding': 'gzip, deflate',
        })

    @abstractmethod
    async def get_article(self, url: str) -> Dict[str, str]:
        """
        通过API获取文章

        Args:
            url: 文章URL

        Returns:
            {
                'success': bool,
                'content': str,
                'source': 'api',  # 标识来源
                'api_name': str,   # API名称
                'error': str
            }
        """
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        判断是否能处理该URL

        Args:
            url: 文章URL

        Returns:
            bool: 是否能处理
        """
        pass

    def extract_doi(self, url: str) -> Optional[str]:
        """从URL中提取DOI"""
        # DOI常见格式
        patterns = [
            r'10\.\d{4,9}/[^\s]+',  # 标准DOI格式
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(0)

        return None

    def _parse_doi_url(self, url: str) -> Optional[str]:
        """
        解析DOI URL
        例如: https://doi.org/10.1000/xyz123
        """
        parsed = urlparse(url)
        if parsed.netloc == 'doi.org':
            return parsed.path.lstrip('/')
        return None


import re


class APIError(Exception):
    """API调用异常"""

    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


class RateLimitError(APIError):
    """速率限制异常"""

    pass


class AuthenticationError(APIError):
    """认证异常"""

    pass
