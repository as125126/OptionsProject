import time
import urllib.parse  # 👈 新增：用於處理連線字串的密碼編碼

import pandas as pd
import pyodbc
from sqlalchemy import create_engine # 👈 新增：SQLAlchemy 核心
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

    def get_engine(self):
        """建立與資料庫的 SQLAlchemy Engine，包含失敗重試機制"""
        # SQLAlchemy URL 格式中，Driver 名稱的空格必須換成 '+'
        # 先移除大括號（如果有的話），再將空格換成 '+'
        formatted_driver = self.driver.strip('{}').replace(' ', '+')

        if self.env == "LOCAL":
            # Local Windows Auth 格式
            conn_url = f"mssql+pyodbc://@{self.server}/{self.database}?driver={formatted_driver}&Trusted_Connection=yes&Encrypt=no"
        else:
            # Azure SQL Login 格式 (密碼必須 URL encode，以免密碼中的特殊符號破壞網址結構)
            encoded_password = urllib.parse.quote_plus(self.password)
            conn_url = f"mssql+pyodbc://{self.username}:{encoded_password}@{self.server}/{self.database}?driver={formatted_driver}&Encrypt=yes&TrustServerCertificate=no"

        max_retries = 3 
        retry_delay = 30 

        for attempt in range(1, max_retries + 1):
            try:
                # 建立 Engine (設定 fast_executemany=True 可以大幅提升未來大量 Insert 的效能)
                engine = create_engine(conn_url, fast_executemany=True)
                
                # 實際測試連線是否成功
                with engine.connect():
                    pass
                return engine

            except Exception as e:
                if attempt == max_retries:
                    print(f"❌ 資料庫連線失敗 (已嘗試 {max_retries} 次)，拋出錯誤...")
                    raise Exception(f"資料庫連線失敗: {e}") from e
                
                print(f"⚠️ 第 {attempt} 次資料庫連線失敗: {e}")
                print(f"⏳ 等待 {retry_delay} 秒後進行重試...")
                time.sleep(retry_delay)

    # ==========================================
    # 以下為 Insert 邏輯 (使用 raw_connection 保留原本的 cursor 寫法)
    # ==========================================
    def insert_major_institutional_options(self, df)-> bool | str:
        if df is None or df.empty:
            print("⚠️ 無資料可寫入")
            return False

        try:
            engine = self.get_engine()
        except Exception as e:
            print(f"❌ 無法取得資料庫 Engine，中止寫入: {e}")
            return False

        # 使用 engine.raw_connection() 取得傳統的 pyodbc 連線，這樣原本的語法完全不用動
        try:
            with engine.raw_connection() as conn:
                cursor = conn.cursor()
                
                first_date_str = str(df["日期"].iloc[0])    
                if len(first_date_str) == 8 and first_date_str.isdigit():
                    target_date = pd.to_datetime(first_date_str, format="%Y%m%d").date()
                else:
                    target_date = pd.to_datetime(first_date_str, format="%Y/%m/%d").date()

                check_sql = "SELECT COUNT(1) FROM [dbo].[MajorInstitutionalTradersOptions] WHERE [Date] = ?"
                cursor.execute(check_sql, (target_date,))
                count = cursor.fetchone()[0]

                if count > 0:
                    print(f"⏩ {target_date} 的資料已存在資料庫中 ({count} 筆)，程式終止寫入以避免重複。")
                    return "EXIST"  
                
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

                for _, row in df.iterrows():
                    date_str = str(row["日期"])    
                    if len(date_str) == 8 and date_str.isdigit():
                        trade_date = pd.to_datetime(date_str, format="%Y%m%d").date()
                    else:
                        trade_date = pd.to_datetime(date_str, format="%Y/%m/%d").date()
                    
                    print(f"🆕 準備寫入 {trade_date}-{row['買賣權別']}-{row['身份別']} 的新資料...")

                    params = (
                        trade_date, row["商品名稱"], row["買賣權別"], row["身份別"],
                        row["買方交易口數"], row["買方交易契約金額(千元)"], row["賣方交易口數"],
                        row["賣方交易契約金額(千元)"], row["交易口數買賣淨額"], row["交易契約金額買賣淨額(千元)"],
                        row["買方未平倉口數"], row["買方未平倉契約金額(千元)"], row["賣方未平倉口數"],
                        row["賣方未平倉契約金額(千元)"], row["未平倉口數買賣淨額"], row["未平倉契約金額買賣淨額(千元)"]
                    )
                    cursor.execute(sql, params)

                conn.commit()
                print(f"✅ 成功寫入 {len(df)} 筆資料至 {self.env} 資料庫")
                return True

        except Exception as e:
            print(f"❌ 寫入資料庫失敗: {e}")
            print(f"錯誤發生在以下資料列：{row.to_dict()}")
            # rollback 會交由 with 區塊與 raw_connection 處理，或可在此顯式呼叫
            return False

    def insert_put_call_ratio(self, df)-> bool | str:
        if df is None or df.empty:
            print("⚠️ 無資料可寫入")
            return False

        try:
            engine = self.get_engine()
        except Exception as e:
            print(f"❌ 無法取得資料庫 Engine，中止寫入: {e}")
            return False

        try:
            with engine.raw_connection() as conn:
                cursor = conn.cursor()
                
                first_date_str = str(df["日期"].iloc[0])    
                if len(first_date_str) == 8 and first_date_str.isdigit():
                    target_date = pd.to_datetime(first_date_str, format="%Y%m%d").date()
                else:
                    target_date = pd.to_datetime(first_date_str, format="%Y/%m/%d").date()

                check_sql = "SELECT COUNT(1) FROM [dbo].[PutCallRatio] WHERE [Date] = ?"
                cursor.execute(check_sql, (target_date,))
                count = cursor.fetchone()[0]

                if count > 0:
                    print(f"⏩ {target_date} 的 P/C Ratio 資料已存在資料庫中 ({count} 筆)，程式終止寫入以避免重複。")
                    return "EXIST"

                sql = """
                    INSERT INTO [dbo].[PutCallRatio] (
                        [Date], [PutVolume], [CallVolume], [PutCallVolumeRatio],
                        [PutOI], [CallOI], [PutCallOIRatio]
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """

                for _, row in df.iterrows():
                    date_str = str(row["日期"])    
                    if len(date_str) == 8 and date_str.isdigit():
                        trade_date = pd.to_datetime(date_str, format="%Y%m%d").date()
                    else:
                        trade_date = pd.to_datetime(date_str, format="%Y/%m/%d").date()
                    
                    print(f"🆕 準備寫入 {trade_date} 的 P/C Ratio 新資料...")

                    params = (
                        trade_date, row["賣權成交量"], row["買權成交量"],
                        row["買賣權成交量比率%"], row["賣權未平倉量"], row["買權未平倉量"],
                        row["買賣權未平倉量比率%"]
                    )
                    cursor.execute(sql, params)

                conn.commit()
                print(f"✅ 成功寫入 {len(df)} 筆 P/C Ratio 資料至 {self.env} 資料庫")
                return True
                
        except Exception as e:
            print(f"❌ 寫入資料庫失敗: {e}")
            return False
        
    # ==========================================
    # 以下為 Fetch 邏輯 (直接把 Engine 餵給 Pandas)
    # ==========================================
    def fetch_latest_options_data(self):
        sql_query = """
        SELECT 
               [Date], [Item], [CallPut], [買方], [賣方], [淨額],
               [買方增減], [賣方增減], [淨額變動]
        FROM [dbo].[v_MajorInstitutionalOptionsAnalysis]
        WHERE [Date] IN (
            SELECT TOP 7 [Date] 
            FROM (SELECT DISTINCT [Date] FROM [dbo].[v_MajorInstitutionalOptionsAnalysis]) AS DistinctDates
            ORDER BY [Date] DESC
        )
        ORDER BY [Date] DESC, [Item], [CallPut];
        """
        
        try:
            engine = self.get_engine()
        except Exception as e:
            print(f"❌ 無法取得資料庫 Engine，中止讀取: {e}")
            return pd.DataFrame()
        
        try:
            print("開始從資料庫撈取近 7 日期權籌碼資料...")     
            
            # 💡 這裡直接傳入 engine，Pandas 的警告就消失了！
            df = pd.read_sql(sql_query, engine)
            
            if df.empty:
                print("⚠️ 警告：資料庫中沒有撈到任何資料。")
            else:
                report_date = df['Date'].iloc[0]
                print(f"✅ 成功撈取最新至 {report_date} 的籌碼資料，共 {len(df)} 筆。")

            return df
        except Exception as e:
            print(f"❌ 資料庫撈取失敗: {str(e)}")
            return pd.DataFrame()

    def fetch_put_call_ratio(self):
        sql_query = """
        SELECT TOP 7
               [Date], [PutVolume], [CallVolume], [PutCallVolumeRatio],
               [PutOI], [CallOI], [PutCallOIRatio]
        FROM [dbo].[PutCallRatio]
        ORDER BY [Date] DESC;
        """
        
        try:
            engine = self.get_engine()
        except Exception as e:
            print(f"❌ 無法取得資料庫 Engine，中止讀取: {e}")
            return pd.DataFrame()
        
        try:
            print("開始從資料庫撈取近 7 日 P/C Ratio 資料...")     

            # 💡 這裡直接傳入 engine
            df = pd.read_sql(sql_query, engine)
            
            if df.empty:
                print("⚠️ 警告：資料庫中沒有撈到任何 P/C Ratio 資料。")
            else:
                df = df.sort_values(by="Date", ascending=True).reset_index(drop=True)
                start_date = df['Date'].iloc[0]
                end_date = df['Date'].iloc[-1]
                print(f"✅ 成功撈取 P/C Ratio 資料，共 {len(df)} 筆。區間：{start_date} ~ {end_date}")

            return df

        except Exception as e:
            print(f"❌ 資料庫撈取失敗: {str(e)}")
            return pd.DataFrame()

    def test_connection(self):
        """測試連線是否正常"""
        try:
            engine = self.get_engine()
            # 建立一次實際的連線測試
            with engine.connect():
                print(f"✅ 成功連線至 {self.env} 資料庫: {self.database}")
            return True
        except Exception as e:
            print(f"❌ 測試連線失敗: {e}")
            return False

if __name__ == "__main__":
    db = DatabaseManager()
    db.test_connection()
    df = db.fetch_latest_options_data()
    if not df.empty:
        print(df.head(6))
    pc_df = db.fetch_put_call_ratio()
    if not pc_df.empty:
        print(pc_df)