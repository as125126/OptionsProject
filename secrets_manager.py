import os
from dotenv import load_dotenv

# 1. 指定 .env 的路徑 (在 config 資料夾下)
dotenv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')

# 2. 載入環境變數
load_dotenv(dotenv_path)

def get_db_password():
    """從環境變數取得資料庫密碼"""
    password = os.getenv('DB_PWD')
    if not password:
        # 這裡可以用我們之後寫的 logger，現在先用 print
        print("警告：找不到資料庫密碼，請檢查 config/.env 檔案")
    return password

if __name__ == "__main__":
    pwd = get_db_password()
    if pwd:
        print(f"成功讀取密碼，長度為: {len(pwd)}")