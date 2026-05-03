import os
from dotenv import load_dotenv

class SecretsManager:
    def __init__(self):
        # 定義 .env 的絕對路徑
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dotenv_path = os.path.join(base_dir, 'config', '.env')
        load_dotenv(dotenv_path)

    def get_db_password(self):
        """從環境變數取得資料庫密碼 (對應 .env 中的 DB_PWD)"""
        # 注意：你在 .env 裡是用 DB_PWD 還是 DB_PASSWORD，這裡要統一
        password = os.getenv('DB_PWD')
        if not password:
            print("⚠️ 警告：找不到資料庫密碼，請檢查 config/.env 檔案")
        return password
    
    def get_email_secrets(self):
        """
        從環境變數或安全空間獲取 Email 機密資訊
        """
        # 這裡可以加入額外的邏輯，例如從 AWS Secrets Manager 抓取
        secrets = {
            "user": os.getenv("SENDER_EMAIL"),
            "password": os.getenv("SENDER_PASSWORD"),
            "host": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "port": int(os.getenv("SMTP_PORT", 587))
        }

        # 安全檢查
        if not secrets["user"] or not secrets["password"]:
            raise ValueError("錯誤：找不到 Email 帳號或密碼，請檢查環境變數設定。")

        return secrets
    
secrets_manager = SecretsManager()

# 建立實例
if __name__ == "__main__":    
    pwd = secrets_manager.get_db_password()
    if pwd:
        print(f"成功讀取密碼，長度為: {len(pwd)}")
    pwd = secrets_manager.get_email_secrets()
    if pwd:
        print(f"成功讀取 Email 機密資訊，使用者: {pwd['user']}, SMTP 伺服器: {pwd['host']}:{pwd['port']}")