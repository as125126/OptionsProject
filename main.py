from database import AzureSQLDatabase

def start_app():
    print("--- 選擇權 & 航運股自動化系統 啟動 ---")
    
    # 1. 初始化資料庫
    db = AzureSQLDatabase()
    
    # 2. 測試連線
    if db.test_connection():
        print("✅ 系統基礎建設檢查通過。")
        # 這裡之後會放：執行爬蟲、資料處理等邏輯
    else:
        print("❌ 系統初始化失敗，請檢查設定。")

if __name__ == "__main__":
    start_app()