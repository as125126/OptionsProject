import pyodbc
from config import cfg
from secrets_manager import secrets_manager 

class DatabaseManager:
    def __init__(self):
        self.db_config = cfg.get_db_config()
        self.env = cfg.env
        
        self.server = self.db_config['SERVER']
        self.database = self.db_config['DATABASE']
        self.driver = self.db_config['DRIVER']
        
        if self.env == "LOCAL":
            print(f"🏠 目前環境：LOCAL (Windows 驗證)")
            self.password = None
        else:
            print(f"☁️ 目前環境：AZURE (SQL Login)")
            self.username = self.db_config.get('USERNAME')
            self.password = secrets_manager.get_db_password()

    def get_connection(self):
        try:
            if self.env == "LOCAL":
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    "Trusted_Connection=yes;"
                    "Encrypt=no;" 
                )
            else:
                conn_str = (
                    f"DRIVER={self.driver};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password};"
                    "Encrypt=yes;"
                    "TrustServerCertificate=no;"
                )
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f"❌ 連線失敗: {e}")
            return None

    def test_connection(self):
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            print(f"✅ 成功連線至 {self.env} 資料庫: {self.database}")
            conn.close()
            return True
        return False

if __name__ == "__main__":
    db = DatabaseManager()
    db.test_connection()