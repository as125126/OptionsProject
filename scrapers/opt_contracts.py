import requests
import pandas as pd
from io import StringIO
from config import cfg
from database import DatabaseManager

class InstitutionalOptionsScraper:
    def __init__(self):
        # 從設定檔取得 URL
        self.url = cfg.get_scraper_config().get("TAIFEX_OPEN_DATA_URL")
        self.db = DatabaseManager()

    def fetch_data(self):
        """從 Open Data API 抓取 CSV 資料"""
        print(f"🚀 正在從 Open Data 抓取資料...")
        try:
            response = requests.get(self.url)
            response.encoding = 'utf-8-sig'  # 期交所 CSV 通常帶有 BOM
            
            if response.status_code == 200:
                # 使用 pandas 讀取 CSV
                df = pd.read_csv(StringIO(response.text))
                return self.process_data(df)
            else:
                print(f"❌ 抓取失敗，狀態碼: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
            return None

    def process_data(self, df):
        """清洗資料：過濾出臺指選擇權並轉換格式"""
        # 1. 欄位名稱校正 (假設 CSV 欄位名稱如下)
        # 日期, 身分別, 商品名稱, 買賣權, 買進口數, 買進金額, 賣出口數, 賣出金額...
        
        # 2. 過濾出「臺指選擇權」
        df_filtered = df[df['商品名稱'].str.contains('臺指選擇權', na=False)].copy()
        
        # 3. 整理成資料庫對應的欄位
        # 這裡根據你資料表 [dbo].[InstitutionalOptions] 的設計來調整
        return df_filtered

    def save_to_db(self, df):
        """將資料存入資料庫"""
        if df is None or df.empty:
            return
        
        conn = self.db.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            for _, row in df.iterrows():
                sql = """
                    INSERT INTO [dbo].[InstitutionalOptions] 
                    (TradeDate, Institution, OptionType, BuyVolume, BuyAmount, SellVolume, SellAmount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                # 這裡的欄位名稱要根據期交所 CSV 的實際標頭修改
                params = (
                    row['日期'], row['身分別'], row['買賣權'], 
                    row['買進口數'], row['買進金額'], row['賣出口數'], row['賣出金額']
                )
                cursor.execute(sql, params)
            
            conn.commit()
            print(f"✅ 成功寫入 {len(df)} 筆資料至 {self.db.env}")
        except Exception as e:
            print(f"❌ 寫入資料庫失敗: {e}")
        finally:
            conn.close()

# 單獨測試區塊
if __name__ == "__main__":
    scraper = InstitutionalOptionsScraper()
    data = scraper.fetch_data()
    
    if data is not None:
        print("\n===== 抓取結果預覽 =====")
        print(data.head())
        
        # 測試連線並詢問是否寫入
        if scraper.db.test_connection():
            # scraper.save_to_db(data) # 測試時先註解掉，確定資料對了再開
            pass