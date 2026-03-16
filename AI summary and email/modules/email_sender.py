"""
发送邮件通知
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Dict


class EmailSender:
    """邮件发送器"""

    def __init__(self, config: Dict):
        self.config = config.get('email', {})

    def send(self, html_file_path: str, report_type: str = "AI学术摘要") -> bool:
        """发送HTML报告邮件"""
        if not self._validate_config():
            print("[FAIL] 邮件配置不完整，跳过发送")
            return False

        try:
            # 读取HTML内容
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 处理收件人列表
            to_recipients = self.config['to']
            if isinstance(to_recipients, list):
                to_recipients_str = ', '.join(to_recipients)
            else:
                to_recipients_str = to_recipients

            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr(("TrendRadar AI", self.config['from']))
            msg['To'] = to_recipients_str
            subject_prefix = self.config.get('subject_prefix', '[AI摘要]')
            msg['Subject'] = f"{subject_prefix} - {report_type}"

            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # 发送邮件
            smtp_port = self.config.get('smtp_port', 587)

            if smtp_port == 465:
                # 使用SSL
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config['smtp_server'], smtp_port, context=context) as server:
                    server.login(self.config['from'], self.config['password'])
                    server.send_message(msg)
            else:
                # 使用STARTTLS
                with smtplib.SMTP(self.config['smtp_server'], smtp_port) as server:
                    server.starttls()
                    server.login(self.config['from'], self.config['password'])
                    server.send_message(msg)

            print(f"[OK] 邮件发送成功 -> {to_recipients_str}")
            return True

        except Exception as e:
            print(f"[FAIL] 邮件发送失败: {e}")
            return False

    def _validate_config(self) -> bool:
        """验证邮件配置是否完整"""
        required_fields = ['from', 'password', 'to', 'smtp_server', 'smtp_port']
        for field in required_fields:
            if not self.config.get(field):
                print(f"邮件配置缺少: {field}")
                return False
        return True


# Test the module directly
if __name__ == '__main__':
    from pathlib import Path
    import yaml

    # Load config
    config_path = Path(__file__).parent.parent / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        print("配置文件不存在，请先创建config.yaml")
        exit(1)

    sender = EmailSender(config)

    # Create test HTML
    test_html = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>测试邮件</title></head>
<body>
    <h1>测试邮件</h1>
    <p>这是一封测试邮件，用于验证邮件发送功能。</p>
</body>
</html>"""

    test_file = Path("output/test_email.html")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_html, encoding='utf-8')

    print("发送测试邮件...")
    result = sender.send(str(test_file), "测试报告")
    print(f"发送结果: {'成功' if result else '失败'}")
