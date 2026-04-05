import pyodbc
import secrets_manager
import json
import os

class AzureSQLDatabase:
    def __init__(self):
        # 1. 讀取 settings.json 裡的非敏感設定
        base_dir = os.path.dirname(os.path.abspath(__file__))
        settings_path = os.path.join(base_dir, 'config', 'settings.json')
        
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            db_config = settings['DATABASE_CONFIG']

        self.server = db_config['SERVER']
        self.database = db_config['DATABASE']
        self.username = db_config['USERNAME']
        self.driver = db_config['DRIVER']
        
        # 2. 透過 secrets_manager 取得密碼
        self.password = secrets_manager.get_db_password()

    def get_connection(self):
        """建立並回傳資料庫連線"""
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
        try:
            return pyodbc.connect(conn_str)
        except pyodbc.Error as e:
            # 針對常見錯誤進行分類 (對 Azure 新手很有幫助)
            sqlstate = e.args[0]
            if "28000" in str(e):
                print("❌ 錯誤：帳號或密碼錯誤。")
            elif "HYT00" in str(e) or "08001" in str(e):
                print("❌ 錯誤：連線逾時。請檢查 Azure SQL 防火牆是否已放行你的 IP。")
            else:
                print(f"❌ 資料庫連線失敗。SQLState: {sqlstate}, 錯誤訊息: {e}")
            return None

    def test_connection(self):
        """簡單測試連線是否成功"""
        conn = self.get_connection()
        if conn:
            print(f"✅ 成功連線至 Azure SQL: {self.database}")
            # 測試執行一個簡單查詢
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            print(f"📊 資料庫版本: {row[0]}")
            conn.close()
            return True
        return False

if __name__ == "__main__":
    db = AzureSQLDatabase()
    db.test_connection()