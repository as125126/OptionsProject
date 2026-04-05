import requests
import pandas as pd
from io import StringIO

def test_fetch_taifex():
    print("--- 開始從期交所抓取資料 ---")
    
    # 1. 設定目標網址 (期交所：三大法人選擇權交易量與未平倉)
    url = "https://www.taifex.com.tw/cht/3/callsAndPutsDate"
    
    # 2. 設定查詢日期 (格式: YYYY/MM/DD)
    payload = {
        'queryDate': '2026/04/02'
    }
    
    try:
        # 3. 發送請求
        response = requests.post(url, data=payload)
        response.encoding = 'utf-8' # 強制使用 utf-8 避免亂碼
        
        # 4. 使用 pandas 直接解析網頁中的所有表格
        # [0] 通常是外層佈局，[1] 之後才是我們要的數據表
        tables = pd.read_html(StringIO(response.text))
        
        # 5. 找出「三大法人」那張表 (通常是表格 index 為 2 或 3)
        # 我們直接把所有抓到的表格名稱跟前幾列印出來看看
        for i, df in enumerate(tables):
            print(f"\n===== 第 {i} 張表 =====")
            print(df) # 直接 print DataFrame
        
                
    except Exception as e:
        print(f"❌ 抓取失敗: {e}")

if __name__ == "__main__":
    test_fetch_taifex()