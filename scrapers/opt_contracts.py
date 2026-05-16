import os
import requests
import pandas as pd
from io import StringIO
from config import cfg
from database import DatabaseManager
from bs4 import BeautifulSoup

# 三大法人-選擇權買賣權分計-依日期
class InstitutionalOptionsScraper:
    def __init__(self):
        # 從設定檔取得 URL
        self.current_url = cfg.get_scraper_config().get("TAIFEX_OPEN_DATA_URL")
        self.history_url = cfg.get_scraper_config().get("TAIFEX_HISTORY_DATA_URL")
        self.web_url = cfg.get_scraper_config().get("TAIFEX_WEB_DATA_URL")

    def export_to_csv(self, data, source_name):
        """
        通用的 CSV 匯出方法
        :param data: DataFrame 資料
        :param source_name: 資料來源名稱 ('API' 或 'WEB')
        :return: 匯出檔案路徑
        """
        if data is None or data.empty:
            print(f"❌ {source_name} 資料為空，無法匯出")
            return None

        # 取得資料日期
        target_date = data["日期"].iloc[0]

        # 建立 export 資料夾
        export_dir = "export"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # 檔名處理
        safe_date_str = str(target_date).replace('/', '-')
        file_name = f"三大法人期權籌碼_{source_name}_{safe_date_str}.csv"
        file_path = os.path.join(export_dir, file_name)

        try:
            data.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"📁 {source_name} 資料已匯出: {file_path}")
            return file_path
        except Exception as e:
            print(f"❌ {source_name} 匯出失敗: {e}")
            return None

    def fetch_API_data(self, start_date=None, end_date=None):
        if start_date and not end_date:
            end_date = start_date

        if start_date and end_date:
            print(f"📅 正在抓取 API 區間資料: {start_date} ~ {end_date} ...")
            url = self.history_url
            payload = {
                "queryStartDate": start_date,
                "queryEndDate": end_date,
                "commodityId": "TXO",
            }
            try:
                response = requests.post(url, data=payload)
            except Exception as e:
                print(f"❌ 歷史資料抓取失敗: {e}")
                return None
        else:
            print("🚀 正在從 Open Data 抓取最新資料...")
            url = self.current_url
            response = requests.get(url)

        if response.status_code == 200:
            text = self._decode_response_text(response)
            df = pd.read_csv(StringIO(text))
            return self.process_data(df)
        else:
            print(f"❌ 抓取失敗，狀態碼: {response.status_code}")
            return None

    def fetch_WEB_data(self):
        """
        從期交所網頁直接爬取 HTML 表格。
        最極簡作法：不帶任何參數，直接 GET 預設網頁，
        期交所就會自動回傳「最新一個交易日」的 TXO 資料。
        """
        print("🌐 正在向期交所請求最新交易日的預設網頁資料...")

        try:
            # 💡 修改：連 payload 都省了！直接用 GET 請求預設網址
            response = requests.get(self.web_url)
            if response.status_code != 200:
                print(f"❌ 網頁請求失敗，狀態碼: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 網頁資料抓取異常: {e}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 💡 從期交所回傳的網頁中(隱藏的日期輸入框)，找出它實際給我們的日期
        date_input = soup.find("input", {"id": "queryDate"})
        if date_input and date_input.get("value"):
            target_date = date_input.get("value")
        else:
            print("❌ 無法從網頁中解析出資料日期")
            return None

        print(f"📅 成功取得最新交易日資料，日期為: {target_date}")

        tables = soup.find_all("table")
        
        if not tables:
            print("⚠️ 網頁中找不到表格資料")
            return None

        # 定義與 Open Data 完全相同的 DataFrame 欄位名稱
        columns = [
            "日期", "商品名稱", "買賣權別", "身份別",
            "買方交易口數", "買方交易契約金額(千元)", "賣方交易口數", "賣方交易契約金額(千元)", 
            "交易口數買賣淨額", "交易契約金額買賣淨額(千元)", "買方未平倉口數", "買方未平倉契約金額(千元)", 
            "賣方未平倉口數", "賣方未平倉契約金額(千元)", "未平倉口數買賣淨額", "未平倉契約金額買賣淨額(千元)"
        ]
        
        parsed_data = []
        table = tables[0]
        rows = table.find_all("tr")
        
        current_call_put = "" # 用來記憶目前是買權還是賣權
        
        for row in rows:
            cols = row.find_all("td")
            # 提取文字並移除千分位逗號
            col_data = [col.text.strip().replace(",", "") for col in cols]
            
            if not col_data:
                continue
            
            if len(col_data) == 16 and col_data[1] == "電子選擇權":
                break  # 遇到電子選擇權就停止，因為我們只要臺指選擇權
            # 處理 HTML 合併儲存格造成的欄位長度差異
            if len(col_data) == 16 and col_data[1] == "臺指選擇權":
                if(col_data[2] == "買權"):
                    current_call_put = "CALL"
                elif(col_data[2] == "賣權"):
                    current_call_put = "PUT"
                else:
                    current_call_put = "ERROR"
                identity = col_data[3]
                values = col_data[4:]
                parsed_data.append([target_date, "臺指選擇權", current_call_put, identity] + values)
                
            elif len(col_data) == 14 and (col_data[0] == "買權" or col_data[0] == "賣權"):
                if(col_data[0] == "買權"):
                    current_call_put = "CALL"
                elif(col_data[0] == "賣權"):
                    current_call_put = "PUT"
                else:
                    current_call_put = "ERROR"
                identity = col_data[1]
                values = col_data[2:]
                parsed_data.append([target_date, "臺指選擇權", current_call_put, identity] + values)
                
            elif len(col_data) == 13 and col_data[0] in ["投信", "外資", "自營商"]:
                identity = col_data[0]
                values = col_data[1:]
                parsed_data.append([target_date, "臺指選擇權", current_call_put, identity] + values)

        if not parsed_data:
            print("⚠️ 網頁有表格，但未能解析出臺指選擇權資料 (可能期交所尚未更新今日籌碼)")
            return pd.DataFrame()
            
        # 轉換為 DataFrame
        df = pd.DataFrame(parsed_data, columns=columns)
        
        # 將數值欄位轉為數字型態 (保護機制)
        for col in columns[4:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        print(f"✅ 網頁資料解析成功！共 {len(df)} 筆。")

        return df

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

        # 替換身份別
        df_filtered["身份別"] = df_filtered["身份別"].replace("外資及陸資", "外資")

        return df_filtered

    def run(self):
        """一鍵執行的主程式邏輯"""
        data= self.fetch_WEB_data()  # 改用網頁爬蟲抓取資料

        if data is not None and not data.empty:
            return DatabaseManager().insert_major_institutional_options(data)
        else:
            print("❌ 沒有符合條件的資料可以處理。")
            return False
        
    # 測試用的獨立方法，讓我們可以直接執行這個檔案來測試爬蟲是否成功抓取資料    
    def test(self):
        """比較 API 和 WEB 資料的測試方法"""
        print("🔄 開始比較 API 和 WEB 資料...\n")

        # 1. 抓取 API 資料
        api_data = self.fetch_API_data()
        if api_data is not None and not api_data.empty:
            print(f"\n✅ API 資料共 {len(api_data)} 筆")
            self.export_to_csv(api_data, "API")
        else:
            print("❌ API 資料取得失敗")

        # 2. 抓取 WEB 資料
        web_data = self.fetch_WEB_data()
        if web_data is not None and not web_data.empty:
            print(f"\n✅ WEB 資料共 {len(web_data)} 筆")
            self.export_to_csv(web_data, "WEB")
        else:
            print("❌ WEB 資料取得失敗")

    def write_API_data_range(self, start_date, end_date):
        data = self.fetch_API_data(start_date, end_date)
        if data is not None and not data.empty:
            return DatabaseManager().insert_major_institutional_options(data)
        else:
            print("❌ 區間資料寫入失敗，沒有資料可寫入。")
            return False

# 單獨測試區塊
if __name__ == "__main__":
    scraper = InstitutionalOptionsScraper()
    # 直接跑 run()，它會自動抓取並寫入資料庫
    flag = "3"
    if(flag == "1"):
        scraper.run()
    elif(flag == "2"):
        scraper.test()
    elif(flag == "3"):
        scraper.write_API_data_range("2026/05/01", "2026/05/14")
