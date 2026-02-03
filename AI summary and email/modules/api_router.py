"""
API路由器 - 根据URL自动选择合适的官方API

协调多个API客户端，提供统一的访问接口。
"""
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .api_client import APIClient
from .springer_api import SpringerAPIClient
from .arxiv_api import ArXivAPIClient
from .elsavier_api import ElsevierAPIClient


class APIRouter:
    """
    API路由器

    根据URL自动选择合适的API客户端获取内容。
    优先使用官方API，避免CAPTCHA问题。
    """

    def __init__(self, config: Dict):
        self.config = config
        self.apis_config = config.get('apis', {})
        self.priority_enabled = config.get('api_priority', {}).get('enabled', True)

        # 初始化所有API客户端
        self.apis: Dict[str, APIClient] = {}

        # 初始化Elsevier API（优先级最高）
        if self.apis_config.get('elsavier', {}).get('enabled', False):
            self.apis['elsavier'] = ElsevierAPIClient(self.apis_config)

        # 初始化arXiv API
        if self.apis_config.get('arxiv', {}).get('enabled', True):
            self.apis['arxiv'] = ArXivAPIClient(self.apis_config)

        # 初始化Springer API
        if self.apis_config.get('springer', {}).get('enabled', True):
            self.apis['springer'] = SpringerAPIClient(self.apis_config)

        # 未来可添加更多API
        # if self.apis_config.get('pubmed', {}).get('enabled'):
        #     from .pubmed_api import PubMedAPIClient
        #     self.apis['pubmed'] = PubMedAPIClient(self.apis_config)

    def identify_api(self, url: str) -> Optional[str]:
        """
        识别URL对应的API

        Args:
            url: 文章URL

        Returns:
            API名称或None
        """
        for api_name, api_client in self.apis.items():
            if api_client.can_handle(url):
                return api_name

        return None

    async def fetch_via_api(self, url: str) -> Dict[str, str]:
        """
        通过API获取内容

        Args:
            url: 文章URL

        Returns:
            {
                'success': bool,
                'content': str,
                'source': str,
                'api_name': str,
                'error': str
            }
        """
        if not self.priority_enabled:
            return {
                'success': False,
                'content': '',
                'error': 'API优先级未启用'
            }

        api_name = self.identify_api(url)

        if api_name and api_name in self.apis:
            try:
                return await self.apis[api_name].get_article(url)
            except Exception as e:
                return {
                    'success': False,
                    'content': '',
                    'error': f'{api_name} API调用失败: {str(e)}'
                }

        return {
            'success': False,
            'content': '',
            'error': 'No API available for this URL',
            'suggestion': self._get_api_suggestion(url)
        }

    def _get_api_suggestion(self, url: str) -> str:
        """返回API访问建议"""
        domain = urlparse(url).netloc.lower()

        suggestions = {
            'sciencedirect.com': 'Elsevier TDM License: https://www.elsevier.com/about/policies-and-standards/text-and-data-mining/license',
            'elsevier.com': 'Elsevier API: https://api.elsevier.com/',
            'springer.com': 'Springer Open Access API (部分开放获取内容免费)',
            'springernature.com': 'Springer Nature Open Access API',
            'nature.com': 'Nature API开放获取内容',
            'arxiv.org': 'arXiv API (完全免费，无需注册)',
            'pubmed.ncbi.nlm.nih.gov': 'PubMed API (完全免费)',
            'ncbi.nlm.nih.gov': 'NCBI API (完全免费)',
            'ieee.org': 'IEEE Xplore API (需要订阅)',
            'dl.acm.org': 'ACM Digital Library API (需要订阅)',
            'informs.org': 'INFORMS PubsOnLine API (需要订阅)',
            'uchicago.edu': 'University of Chicago Press - Cloudflare Turnstile保护，无法自动化访问',
            'oup.com': 'Oxford University Press - Cloudflare保护，无法自动化访问',
        }

        for key, suggestion in suggestions.items():
            if key in domain:
                return suggestion

        return "检查出版商是否提供官方API访问"

    def get_supported_domains(self) -> List[str]:
        """获取支持的域名列表"""
        domains = []

        if 'arxiv' in self.apis:
            domains.extend(list(ArXivAPIClient.ARXIV_DOMAINS))

        if 'springer' in self.apis:
            domains.extend(list(SpringerAPIClient.SPRINGER_DOMAINS))

        if 'elsavier' in self.apis:
            domains.extend(list(ElsevierAPIClient.ELSEVIER_DOMAINS))

        return sorted(set(domains))

    def get_status(self) -> Dict:
        """获取API路由器状态"""
        return {
            'priority_enabled': self.priority_enabled,
            'available_apis': list(self.apis.keys()),
            'supported_domains': self.get_supported_domains()
        }


# CAPTCHA检测器
class CAPTCHADetector:
    """
    CAPTCHA检测器

    检测页面是否显示CAPTCHA验证
    """

    # CAPTCHA指示器关键词和类型
    CAPTCHA_INDICATORS = {
        'Are you a robot?': 'custom',
        'recaptcha': 'recaptcha_v2',
        'hcaptcha': 'hcaptcha',
        'cf-challenge': 'cloudflare',
        'challenge-platform': 'cloudflare',
        'Just a moment': 'cloudflare',
        'Checking your browser': 'cloudflare',
        'Human verification': 'custom',
        'Please verify you are a human': 'custom',
    }

    @staticmethod
    def detect_captcha(page_content: str, url: str = '') -> Dict:
        """
        检测CAPTCHA

        Args:
            page_content: 页面HTML内容
            url: 页面URL（可选，用于上下文）

        Returns:
            {
                'has_captcha': bool,
                'type': str,
                'sitekey': str,
                'action_required': str
            }
        """
        content_lower = page_content.lower()

        # 检测各种CAPTCHA指示器
        for indicator, captcha_type in CAPTCHADetector.CAPTCHA_INDICATORS.items():
            if indicator.lower() in content_lower:
                # 尝试提取sitekey（对于reCAPTCHA）
                sitekey = CAPTCHADetector._extract_sitekey(page_content)

                return {
                    'has_captcha': True,
                    'type': captcha_type,
                    'sitekey': sitekey,
                    'action_required': f'检测到{captcha_type}验证，需要官方API访问'
                }

        # 检测常见的CAPTCHA框架
        captcha_patterns = [
            (r'data-sitekey="([^"]+)"', 'recaptcha_v2'),
            (r'captcha-sitekey["\s:]+([^\s"\']+)', 'recaptcha_v2'),
            (r'hcaptcha\.com', 'hcaptcha'),
            (r'challenges\.cloudflare\.com', 'cloudflare'),
            (r'cloudflare-challenge', 'cloudflare'),
        ]

        for pattern, captcha_type in captcha_patterns:
            match = re.search(pattern, page_content, re.IGNORECASE)
            if match:
                return {
                    'has_captcha': True,
                    'type': captcha_type,
                    'sitekey': match.group(1) if match.groups() else '',
                    'action_required': f'检测到{captcha_type}验证'
                }

        return {
            'has_captcha': False,
            'type': None,
            'sitekey': '',
            'action_required': ''
        }

    @staticmethod
    def _extract_sitekey(content: str) -> str:
        """提取reCAPTCHA sitekey"""
        patterns = [
            r'data-sitekey="([^"]+)"',
            r'"sitekey"\s*:\s*"([^"]+)"',
            r"sitekey['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)

        return ''

    @staticmethod
    def is_captcha_error(error: str) -> bool:
        """判断错误消息是否与CAPTCHA相关"""
        captcha_keywords = [
            'captcha',
            'robot',
            'challenge',
            'verification',
            'cloudflare',
            'access denied',
            '403',
        ]

        error_lower = error.lower()
        return any(keyword in error_lower for keyword in captcha_keywords)


import re


# 测试
if __name__ == '__main__':
    import asyncio

    async def test():
        config = {
            'apis': {
                'arxiv': {'enabled': True},
                'springer': {'enabled': True, 'open_access_only': True}
            },
            'api_priority': {
                'enabled': True
            }
        }

        router = APIRouter(config)

        print("API路由器状态:")
        print(router.get_status())
        print(f"\n支持的域名: {router.get_supported_domains()}")

        # 测试URL识别
        test_urls = [
            "https://arxiv.org/abs/2301.12345",
            "https://link.springer.com/article/10.1007/s00148-021-00858-6",
            "https://www.sciencedirect.com/science/article/pii/S000000000000000",
        ]

        print("\nURL识别测试:")
        for url in test_urls:
            api_name = router.identify_api(url)
            print(f"  {url}")
            print(f"    -> API: {api_name or 'None'}")

        # 测试CAPTCHA检测
        print("\nCAPTCHA检测测试:")
        test_pages = [
            ("正常页面", "<html><body>This is a normal page</body></html>"),
            ("Cloudflare", "<html><title>Just a moment...</title>Checking your browser</html>"),
            ("reCAPTCHA", '<html><div class="g-recaptcha" data-sitekey="12345"></div></html>'),
        ]

        for name, content in test_pages:
            result = CAPTCHADetector.detect_captcha(content)
            print(f"  {name}: {'CAPTCHA' if result['has_captcha'] else '正常'}")
            if result['has_captcha']:
                print(f"    类型: {result['type']}")

    asyncio.run(test())
