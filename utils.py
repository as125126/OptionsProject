from datetime import datetime
import pandas as pd

def to_datetime(date_val):
    """
    內部輔助工具：將各種常見的日期型態（str, datetime, Timestamp）統一轉換為 pandas.Timestamp
    """
    if pd.isna(date_val):
        return None
    if isinstance(date_val, (datetime, pd.Timestamp)):
        return pd.to_datetime(date_val)
    
    # 處理字串型態，自動相容 YYYY-MM-DD 或 YYYY/MM/DD
    date_str = str(date_val).strip()
    if "/" in date_str:
        return pd.to_datetime(date_str, format="%Y/%m/%d")
    elif "-" in date_str:
        return pd.to_datetime(date_str, format="%Y-%m-%d")
    else:
        # 嘗試讓 pandas 自行解析
        return pd.to_datetime(date_str, errors='coerce')

def get_date_with_weekday(date_val, format_str="%m/%d"):
    """
    將日期轉換為帶有中文星期的字串，例如：'05/15 (五)'
    
    :param date_val: 支援 字串(YYYY-MM-DD 或 YYYY/MM/DD)、datetime 或 Timestamp
    :param format_str: 日期的格式，預設為 '%m/%d'
    :return: str，例如 '05/15 (五)'，若解析失敗回傳空字串
    """
    dt = to_datetime(date_val)
    if dt is None or pd.isna(dt):
        return ""
    
    weekdays = ["(一)", "(二)", "(三)", "(四)", "(五)", "(六)", "(日)"]
    w_str = weekdays[dt.dayofweek]
    
    return f"{dt.strftime(format_str)} {w_str}"

# 獨立單獨執行時的測試區塊
if __name__ == "__main__":
    print("--- 開始測試 date_utils 模組功能 ---")
    
    # 測試 1：一般交易日 (星期五)
    test_date1 = "2026-05-15" 
    print(f"輸入 {test_date1} -> 顯示: {get_date_with_weekday(test_date1)}")    

   