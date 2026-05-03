import sys
# 1. 匯入你的爬蟲類別
from scrapers.opt_contracts import InstitutionalOptionsScraper
# 2. 匯入你的寄信報表模組
from send_email import send_daily_options_report

def main():
    print("🚀 =======================================")
    print("🚀 開始執行期權籌碼自動化專案")
    print("🚀 =======================================\n")
    
    try:
        # ==========================================
        # 階段 1：爬取資料與寫入資料庫
        # ==========================================
        print("▶️ [階段一] 啟動資料爬蟲作業...")
        
        # 實例化你的爬蟲類別
        scraper = InstitutionalOptionsScraper()
        
        # 執行爬取與寫入 (你已經把寫入資料庫的邏輯包在 run() 裡面了)
        # 所以只要這行跑完，資料就會出現在資料庫裡
        scraper.run()
        
        print("✅ [階段一] 爬蟲與寫入作業完成。\n")

        # ==========================================
        # 階段 2：產生報表並寄出 Email
        # ==========================================
        print("▶️ [階段二] 啟動自動報表與寄件作業...")
        
        # 呼叫我們封裝好的寄信流程 (從 DB 撈最新一天 -> 轉 HTML -> 寄信)
        email_success = send_daily_options_report()
        
        if email_success:
            print("\n🎉 今日期權籌碼自動化任務全數圓滿完成！")
        else:
            print("\n⚠️ 寄信任務未成功，請檢查上方錯誤訊息。")
            
    except Exception as e:
        print(f"\n❌ 執行過程中發生致命錯誤: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()