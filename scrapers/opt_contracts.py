import requests
import pandas as pd
from io import StringIO
from config import cfg
from database import DatabaseManager


# 三大法人-選擇權買賣權分計-依日期
class InstitutionalOptionsScraper:
    def __init__(self):
        # 從設定檔取得 URL
        self.current_url = cfg.get_scraper_config().get("TAIFEX_OPEN_DATA_URL")
        self.history_url = cfg.get_scraper_config().get("TAIFEX_HISTORY_DATA_URL")

        self.db = DatabaseManager()

    def fetch_data(self, target_date=None):
        """
        抓取資料。
        :param target_date: 字串格式 'YYYY/MM/DD'，例如 '2024/04/01'。
                            若為 None，則抓取 Open Data 最新資料。
        """
        if target_date:
            # 歷史資料下載 URL (範例格式，需對應期交所實際 post 請求或網址)
            # 注意：抓取歷史資料通常需要使用 POST 請求並帶入日期參數
            print(f"📅 正在抓取特定日期資料: {target_date}...")
            url = self.history_url
            payload = {
                "queryStartDate": target_date,
                "queryEndDate": target_date,
                "commodityId": "TXO",  # 臺指選擇權
            }
            try:
                response = requests.post(url, data=payload)
            except Exception as e:
                print(f"❌ 歷史資料抓取失敗: {e}")
                return None
        else:
            # 原本的 Open Data 邏輯：抓取最新一筆
            print(f"🚀 正在從 Open Data 抓取最新資料...")
            url = self.current_url
            response = requests.get(url)

        if response.status_code == 200:
            text = self._decode_response_text(response)
            df = pd.read_csv(StringIO(text))
            # 清洗資料：過濾出臺指選擇權並轉換格式
            return self.process_data(df)
        else:
            print(f"❌ 抓取失敗，狀態碼: {response.status_code}")
            return None

    def _decode_response_text(self, response):
        """自動偵測並解碼 HTTP 回傳內容，避免亂碼。"""
        encoding = response.encoding
        if not encoding or encoding.lower() in {"iso-8859-1", "latin-1"}:
            encoding = response.apparent_encoding or "utf-8"
        response.encoding = encoding
        try:
            return response.text
        except Exception:
            return response.content.decode(encoding or "utf-8", errors="replace")

    def process_data(self, df):
        """資料清洗：只留下『臺指選擇權』"""
        if df is None:
            return None

        # 篩選：只抓『商品名稱』欄位包含『臺指選擇權』的資料
        df_filtered = df[df["商品名稱"].str.contains("臺指選擇權", na=False)].copy()
        return df_filtered

    def run(self):
        """一鍵執行的主程式邏輯"""
        data = self.fetch_data()

        if data is not None and not data.empty:
            print("\n----- 資料預覽 -----")
            print(data.head(6))  # 先印出前幾行給你看
            # for row_idx, row in data.iterrows():
            #     print(f"\n----- 第 {row_idx} 筆 -----")
            #     print("日期:", row["日期"])
            #     print("商品名稱:", row["商品名稱"])
            #     print("買賣權別:", row["買賣權別"])
            #     print("身份別:", row["身份別"])
            #     print("買方交易口數:", row["買方交易口數"])
            #     print("買方交易契約金額(千元):", row["買方交易契約金額(千元)"])
            #     print("賣方交易口數:", row["賣方交易口數"])
            #     print("賣方交易契約金額(千元):", row["賣方交易契約金額(千元)"])
            #     print("交易口數買賣淨額:", row["交易口數買賣淨額"])
            #     print("交易契約金額買賣淨額(千元):", row["交易契約金額買賣淨額(千元)"])
            #     print("買方未平倉口數:", row["買方未平倉口數"])
            #     print("買方未平倉契約金額(千元):", row["買方未平倉契約金額(千元)"])
            #     print("賣方未平倉口數:", row["賣方未平倉口數"])
            #     print("賣方未平倉契約金額(千元):", row["賣方未平倉契約金額(千元)"])
            #     print("未平倉口數買賣淨額:", row["未平倉口數買賣淨額"])
            #     print("未平倉契約金額買賣淨額(千元):", row["未平倉契約金額買賣淨額(千元)"])
            # 呼叫 database.py 裡面的專業寫入函式
            self.db.insert_major_institutional_options(data)
        else:
            print("❌ 沒有符合條件的資料可以處理。")


# 單獨測試區塊
if __name__ == "__main__":
    scraper = InstitutionalOptionsScraper()
    # 直接跑 run()，它會自動抓取並寫入資料庫
    scraper.run()
