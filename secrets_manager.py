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

# 建立實例
secrets_manager = SecretsManager()

if __name__ == "__main__":
    pwd = secrets_manager.get_db_password()
    if pwd:
        print(f"成功讀取密碼，長度為: {len(pwd)}")