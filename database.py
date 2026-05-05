import time

import pyodbc
import pandas as pd
from config import cfg
from secrets_manager import secrets_manager


class DatabaseManager:
    def __init__(self):
        self.db_config = cfg.get_db_config()
        self.env = cfg.env

        self.server = self.db_config["SERVER"]
        self.database = self.db_config["DATABASE"]
        self.driver = self.db_config["DRIVER"]

        if self.env == "LOCAL":
            print(f"🏠 目前環境：LOCAL (Windows 驗證)")
            self.password = None
        else:
            print(f"☁️ 目前環境：AZURE (SQL Login)")
            self.username = self.db_config.get("USERNAME")
            self.password = secrets_manager.get_db_password()

    def get_connection(self):
        """建立與資料庫的連線，包含失敗重試機制"""
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

        max_retries = 2 # 總共嘗試次數：第 1 次 + 重試 1 次
        retry_delay = 30 # 重試間隔秒數

        for attempt in range(1, max_retries + 1):
            try:
                # 嘗試建立連線
                return pyodbc.connect(conn_str)
            except Exception as e:
                # 如果是最後一次嘗試，則拋出例外
                if attempt == max_retries:
                    print(f"❌ 資料庫連線失敗 (已嘗試 {max_retries} 次)，拋出錯誤...")
                    raise Exception(f"資料庫連線失敗: {e}") from e
                
                # 如果不是最後一次，則等待並重試
                print(f"⚠️ 第 {attempt} 次資料庫連線失敗: {e}")
                print(f"⏳ 等待 {retry_delay} 秒後進行重試...")
                time.sleep(retry_delay)

    # 三大法人-選擇權買賣權分計-依日期 Insert
    def insert_major_institutional_options(self, df):
        """
        將 API 抓取的資料映射到 MajorInstitutionalTradersOptions 表格中。
        寫入前會先 SELECT 檢查該日資料是否已存在，若存在則略過寫入。
        """
        if df is None or df.empty:
            print("⚠️ 無資料可寫入")
            return False

        try:
            conn = self.get_connection()
        except Exception as e:
            # 捕獲 get_connection 拋出的異常
            print(f"❌ 無法取得資料庫連線，中止寫入: {e}")
            return False

        cursor = conn.cursor()
        try:
            # ==========================================
            # 💡 新增：取得資料日期，並 SELECT 檢查是否已存在
            # ==========================================
            first_date_str = str(df["日期"].iloc[0])    
            if len(first_date_str) == 8 and first_date_str.isdigit():
                target_date = pd.to_datetime(first_date_str, format="%Y%m%d").date()
            else:
                target_date = pd.to_datetime(first_date_str, format="%Y/%m/%d").date()

            check_sql = "SELECT COUNT(1) FROM [dbo].[MajorInstitutionalTradersOptions] WHERE [Date] = ?"
            cursor.execute(check_sql, (target_date,))
            count = cursor.fetchone()[0]

            if count > 0:
                # 如果已經有資料，就印出提示並提早結束這個 Function
                print(f"⏩ {target_date} 的資料已存在資料庫中 ({count} 筆)，程式終止寫入以避免重複。")
                return "EXIST"  # 👈 將原本的 False 改成 "EXIST"
            else:
                print(f"🆕 準備寫入 {target_date} 的新資料...")
            
            # ==========================================
            # 確認無資料後，開始執行寫入邏輯
            # ==========================================
            sql = """
                INSERT INTO [dbo].[MajorInstitutionalTradersOptions] (
                    [Date], [ContractCode], [CallPut], [Item],
                    [TradingVolume_Long], [TradingValue_Long],
                    [TradingVolume_Short], [TradingValue_Short],
                    [TradingVolume_Net], [TradingValue_Net],
                    [OpenInterest_Long], [OpenInterest_Long_Value],
                    [OpenInterest_Short], [OpenInterest_Short_Value],
                    [OpenInterest_Net], [OpenInterest_Net_Value]
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # 遍歷 DataFrame 並將資料填入
            for _, row in df.iterrows():
                date_str = str(row["日期"])    
                if len(date_str) == 8 and date_str.isdigit():
                    # 假設是 yyyymmdd 格式
                    trade_date = pd.to_datetime(date_str, format="%Y%m%d").date()
                else:
                    # 假設是 yyyy/mm/dd 格式
                    trade_date = pd.to_datetime(date_str, format="%Y/%m/%d").date()
                    
                params = (
                    trade_date,
                    row["商品名稱"],
                    row["買賣權別"],
                    row["身份別"],
                    # 交易部分
                    row["買方交易口數"],
                    row["買方交易契約金額(千元)"] ,
                    row["賣方交易口數"],
                    row["賣方交易契約金額(千元)"] ,
                    row["交易口數買賣淨額"],
                    row["交易契約金額買賣淨額(千元)"] ,
                    # 未平倉部分
                    row["買方未平倉口數"],
                    row["買方未平倉契約金額(千元)"] ,
                    row["賣方未平倉口數"],
                    row["賣方未平倉契約金額(千元)"] ,
                    row["未平倉口數買賣淨額"],
                    row["未平倉契約金額買賣淨額(千元)"] ,
                )
                cursor.execute(sql, params)

            conn.commit()
            print(f"✅ 成功寫入 {len(df)} 筆資料至 {self.env} 資料庫")
            return True

        except Exception as e:
            print(f"❌ 寫入資料庫失敗: {e}")
            conn.rollback() # 發生錯誤時退回，避免寫入不完整的髒資料
            return False
        finally:
            conn.close()

    def fetch_latest_options_data(self):
        """
        從資料庫 View 中撈取「最新一個交易日」的三大法人期權籌碼資料。
        預期會撈出 6 筆紀錄 (外資、投信、自營商 各有 CALL 與 PUT)。

        :param engine: SQLAlchemy engine 或 pyodbc connection 物件
        :return: 包含查詢結果的 Pandas DataFrame
        """

        sql_query = """
        SELECT 
               [Date]
              ,[Item]
              ,[CallPut]
              ,[買方]
              ,[賣方]
              ,[淨額]
              ,[買方增減]
              ,[賣方增減]
              ,[淨額變動]
        FROM [dbo].[v_MajorInstitutionalOptionsAnalysis]
        WHERE [Date] = (
            SELECT MAX([Date]) 
            FROM [dbo].[v_MajorInstitutionalOptionsAnalysis]
        )
        ORDER BY [Item], [CallPut];
        """
        
        try:
            conn = self.get_connection()
        except Exception as e:
            print(f"❌ 無法取得資料庫連線，中止讀取: {e}")
            return pd.DataFrame()
        
        try:
            print("開始從資料庫撈取最新期權籌碼資料...")     

            df = pd.read_sql(sql_query, conn)
            
            if df.empty:
                print("⚠️ 警告：資料庫中沒有撈到任何資料。")
            else:
                # 取得撈到的日期印出來確認
                report_date = df['Date'].iloc[0]
                print(f"✅ 成功撈取 {report_date} 的籌碼資料，共 {len(df)} 筆。")

            return df

        except Exception as e:
            print(f"❌ 資料庫撈取失敗: {str(e)}")
            # 發生錯誤時回傳空的 DataFrame，避免後續程式直接崩潰
            return pd.DataFrame()
        finally:
            conn.close()

    def test_connection(self):
        """測試連線是否正常"""
        try:
            conn = self.get_connection()
            print(f"✅ 成功連線至 {self.env} 資料庫: {self.database}")
            conn.close()
            return True
        except Exception as e:
            print(f"❌ 測試連線失敗: {e}")
            return False

if __name__ == "__main__":
    db = DatabaseManager()
    db.test_connection()
    # 測試撈取資料
    df = db.fetch_latest_options_data()
    if not df.empty:
        print(df.head(6))