import pyodbc
import sys
from config import cfg  # 讀取設定載入器
from secrets_manager import secrets_manager  # 讀取金鑰管理員

class DatabaseManager:
    def __init__(self):
        # 1. 從 config.py 取得目前環境設定 (LOCAL 或 AZURE)
        self.db_config = cfg.get_db_config()
        self.env = cfg.env
        
        # 2. 基本連線參數
        self.server = self.db_config['SERVER']
        self.database = self.db_config['DATABASE']
        self.driver = self.db_config['DRIVER']
        
        # 3. 根據環境處理認證資訊
        if self.env == "LOCAL":
            self.username = None
            self.password = None
            print(f"🏠 目前環境：LOCAL (使用 Windows 驗證)")
        else:
            # 雲端環境：透過 SecretsManager 取得敏感資訊
            secrets = secrets_manager
            self.username = self.db_config.get('USERNAME')
            self.password = secrets.get_db_password() # 從 .env 抓取
            print(f"☁️ 目前環境：AZURE (使用 SQL Login)")

    def get_connection(self):
        """根據環境建立並回傳 pyodbc 連線物件"""
        try:
            if self.env == "LOCAL":
                # 本機連線：Trusted_Connection 代表使用目前的 Windows 帳號
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    "Trusted_Connection=yes;"
                    "Encrypt=no;" 
                )
            else:
                # Azure 連線：需要帳密，且強制開啟加密 (Encrypt=yes)
                if not self.password:
                    raise ValueError("錯誤：找不到 Azure 資料庫密碼，請檢查 .env 檔")
                
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password};"
                    "Encrypt=yes;"
                    "TrustServerCertificate=no;"
                    "Connection Timeout=30;"
                )
            
            return pyodbc.connect(conn_str)
            
        except Exception as e:
            print(f"❌ 資料庫連線失敗 [{self.env}]: {e}")
            return None

    def test_connection(self):
        """測試連線並印出資料庫版本"""
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            print(f"✅ 連線成功！")
            print(f"📊 資料庫版本: {row[0]}")
            conn.close()
            return True
        return False

# 測試腳本
if __name__ == "__main__":
    db = DatabaseManager()
    db.test_connection()