"""
AI学术文章摘要与邮件推送系统

模块列表:
- browser_automation: 浏览器自动化（API优先）
- api_client: API客户端基类
- api_router: API路由器和CAPTCHA检测器
- arxiv_api: arXiv API客户端
- springer_api: Springer API客户端
"""

from .browser_automation import BrowserAutomation
from .api_client import APIClient, APIError, RateLimitError, AuthenticationError
from .api_router import APIRouter, CAPTCHADetector
from .arxiv_api import ArXivAPIClient
from .springer_api import SpringerAPIClient
from .elsavier_api import ElsevierAPIClient

__all__ = [
    'BrowserAutomation',
    'APIClient',
    'APIError',
    'RateLimitError',
    'AuthenticationError',
    'APIRouter',
    'CAPTCHADetector',
    'ArXivAPIClient',
    'SpringerAPIClient',
    'ElsevierAPIClient',
]
