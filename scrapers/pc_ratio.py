from datetime import datetime
import os
import requests
import pandas as pd
from config import cfg
from database import DatabaseManager
from bs4 import BeautifulSoup


# 三大法人-選擇權買賣權分計-依日期
class PutCallRatioOptionsScraper:
    def __init__(self):
        # 從設定檔取得 URL
        self.web_url = cfg.get_scraper_config().get("TAIFEX_WEB_PC_RATIO_URL")

    def export_to_csv(self, data, source_name):
        """
        通用的 CSV 匯出方法
        :param data: DataFrame 資料
        :param source_name: 
        :return: 匯出檔案路徑
        """
        if data is None or data.empty:
            print(f"❌ {source_name} 資料為空，無法匯出")
            return None

        # 建立 export 資料夾
        export_dir = "export"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # 檔名處理
        file_name = f"{source_name}.csv"
        file_path = os.path.join(export_dir, file_name)

        try:
            data.to_csv(file_path, index=False, encoding="utf-8-sig")
            print(f"📁 {source_name} 資料已匯出: {file_path}")
            return file_path
        except Exception as e:
            print(f"❌ {source_name} 匯出失敗: {e}")
            return None

    def fetch_WEB_data(self, start_date=None, end_date=None):
        """
        從期交所網頁抓取 P/C Ratio 資料。
        - 若未指定日期: 預設抓取網頁近 30 天資料，並只回傳「最新一個交易日」。
        - 若有指定日期 (例如 "2026/05/01"): 發送 POST 請求，回傳該區間的所有資料。
        """
        
        # 1. 決定請求方式與參數
        if start_date and end_date:
            print(f"🌐 正在向期交所請求 P/C Ratio 資料，區間: {start_date} ~ {end_date}...")
            payload = {
                "queryStartDate": start_date,
                "queryEndDate": end_date
            }
            try:
                # 查詢特定區間需要用 POST 並帶上 payload
                response = requests.post(self.web_url, data=payload)
                if response.status_code != 200:
                    print(f"❌ 網頁請求失敗，狀態碼: {response.status_code}")
                    return None
            except Exception as e:
                print(f"❌ 網頁資料抓取異常: {e}")
                return None
        else:
            print("🌐 正在向期交所請求 P/C Ratio 預設網頁資料 (最新單日)...")
            try:
                # 未指定日期時，直接用 GET 取得預設網頁
                response = requests.get(self.web_url)
                if response.status_code != 200:
                    print(f"❌ 網頁請求失敗，狀態碼: {response.status_code}")
                    return None
            except Exception as e:
                print(f"❌ 網頁資料抓取異常: {e}")
                return None

        # 2. 解析 HTML 表格
        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table")

        if not tables:
            print("⚠️ 網頁中找不到表格資料")
            return None

        columns = [
            "日期",
            "賣權成交量",
            "買權成交量",
            "買賣權成交量比率%",
            "賣權未平倉量",
            "買權未平倉量",
            "買賣權未平倉量比率%",
        ]

        parsed_data = []

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                col_data = [col.text.strip().replace(",", "") for col in cols]

                if len(col_data) != 7:
                    continue

                try:
                    datetime.strptime(col_data[0], '%Y/%m/%d')
                except ValueError:
                    continue

                parsed_data.append(col_data)               

        if not parsed_data:
            print("⚠️ 網頁有表格，但未能解析出區間內的 P/C Ratio 資料 (可能該區間無交易日)")
            return pd.DataFrame()

        # 3. 轉換與清洗 DataFrame
        df = pd.DataFrame(parsed_data, columns=columns)
        df["日期"] = pd.to_datetime(df["日期"], format="%Y/%m/%d")
        df = df.sort_values(by="日期", ascending=False).reset_index(drop=True)

        # 4. 根據是否有指定區間，決定回傳筆數
        if start_date and end_date:
            # 若有指定區間，回傳全部爬到的結果
            result_df = df.copy()
        else:
            # 若未指定，只保留最新的一天
            result_df = df.head(1).copy()

        # 日期轉回字串格式 (YYYY/MM/DD) 以利資料庫儲存
        result_df["日期"] = result_df["日期"].dt.strftime("%Y/%m/%d")

        # 數值型態轉換
        for col in columns[1:]:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce")

        return result_df

    def run(self):
        """一鍵執行的主程式邏輯"""
        data = self.fetch_WEB_data()

        if data is not None and not data.empty:
            return DatabaseManager().insert_put_call_ratio(data)
        else:
            print("❌ 沒有符合條件的資料可以處理。")
            return False

    # 測試用的獨立方法，讓我們可以直接執行這個檔案來測試爬蟲是否成功抓取資料
    def test(self):
        """測試用的獨立方法"""
        print("\n=== 測試 1: 抓取最新單日資料 ===")
        latest_data = self.fetch_WEB_data()
        if latest_data is not None and not latest_data.empty:
            print(f"✅ 最新資料共 {len(latest_data)} 筆，日期: {latest_data['日期'].iloc[0]}")
            # 取得資料日期
            target_date = latest_data["日期"].iloc[0]
            safe_date_str = str(target_date).replace("/", "-")
            self.export_to_csv(latest_data, f"PCRatio_Latest{safe_date_str}")
        else:
            print("❌ 最新資料取得失敗")

    def test_range(self,start_d,end_d):
        """測試用的獨立方法，專門測試抓取指定區間資料"""
        print("\n=== 測試: 抓取指定區間資料 ===")
        range_data = self.fetch_WEB_data(start_d, end_d)
        
        if range_data is not None and not range_data.empty:
            print(f"✅ 區間資料共 {len(range_data)} 筆")
            # 這裡稍微調整檔名，避免蓋過前面的檔案
            safe_start = start_d.replace("/", "")
            safe_end = end_d.replace("/", "")
            self.export_to_csv(range_data, f"PCRatio_Range_{safe_start}_{safe_end}")
            DatabaseManager().insert_put_call_ratio(range_data)
        else:
            print("❌ 區間資料取得失敗")


# 單獨測試區塊
if __name__ == "__main__":
    scraper = PutCallRatioOptionsScraper()
    # 直接跑 run()，它會自動抓取並寫入資料庫
    flag = "3"
    if flag == "1":
        scraper.run()
    elif flag == "2":
        scraper.test()
    elif(flag == "3"):
        scraper.test_range("2026/05/01", "2026/05/14")
