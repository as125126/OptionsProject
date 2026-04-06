import json
import os

# 取得目前檔案所在目錄的絕對路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'config', 'settings.json')

class Config:
    def __init__(self):
        self.data = self._load_json()
        self.env = self.data.get("ENV", "LOCAL")

    def _load_json(self):
        if not os.path.exists(SETTINGS_FILE):
            raise FileNotFoundError(f"找不到設定檔：{SETTINGS_FILE}")
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_db_config(self):
        """根據 ENV 自動回傳 LOCAL 或 AZURE 的設定段落"""
        return self.data["DATABASE"].get(self.env)

# 建立單一實例供全域使用
cfg = Config()

if __name__ == "__main__":
    # 快速測試是否讀取正確
    db_info = cfg.get_db_config()
    print(f"目前環境: {cfg.env}")
    print(f"目標資料庫: {db_info['DATABASE']}")