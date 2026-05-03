# send_email.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from secrets_manager import secrets_manager

logger = logging.getLogger(__name__)

def send_html_email(recipient_email, subject, html_content):
    """
    透過 secrets_manager 取得金鑰並寄信
    """
    try:
        # 向 secrets_manager 要機密資訊
        creds = secrets_manager.get_email_secrets()
        
        msg = MIMEMultipart()
        msg['From'] = creds["user"]
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        with smtplib.SMTP(creds["host"], creds["port"]) as server:
            server.starttls()
            server.login(creds["user"], creds["password"])
            server.send_message(msg)
            
        logger.info(f"郵件發送成功: {subject}")
        return True
    except Exception as e:
        logger.error(f"郵件發送過程出錯: {str(e)}")
        return False

if __name__ == "__main__":
    # 測試 logic
    print("測試 secrets_manager 整合...")
    # 寄測試信給自己
    my_creds = secrets_manager.get_email_secrets()
    send_html_email(my_creds["user"], "Secrets Manager Test", "<h1>連線成功</h1>")