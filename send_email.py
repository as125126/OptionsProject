import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd

# 匯入我們自己寫的模組
from secrets_manager import secrets_manager
from database import DatabaseManager
from report_generator import generate_options_html
from utils import get_date_with_weekday

def send_html_email(subject, html_content):
    """
    核心寄信功能：只負責把準備好的 HTML 寄出去[cite: 6]
    """
    try:
        # 向 secrets_manager 要機密資訊
        creds = secrets_manager.get_email_secrets()

        msg = MIMEMultipart()
        msg["From"] = creds["user"]
        msg["To"] = creds["user"]
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        print(f"正在連線至 SMTP 伺服器寄信給 {creds['user']} ...")
        with smtplib.SMTP(creds["host"], creds["port"]) as server:
            server.starttls()
            server.login(creds["user"], creds["password"])
            server.send_message(msg)

        print(f"✅ 郵件發送成功: {subject}")
        return True
    except Exception as e:
        print(f"❌ 郵件發送過程出錯: {str(e)}")
        return False


def send_daily_options_report():
    """
    封裝好的自動化流程：撈資料 -> 產報表 -> 寄信[cite: 6]
    """
    print("開始準備每日期權籌碼報表...")

    # 1. 撈取資料
    db = DatabaseManager()
    df = db.fetch_latest_options_data()
    pc_df = db.fetch_put_call_ratio()

    if df is None or df.empty:
        print("⚠️ 今日資料庫無資料，取消寄信作業。")
        return False

    # 2. 取得日期以設定信件主旨
    raw_date = df["Date"].iloc[0]
    report_date = get_date_with_weekday(raw_date, format_str="%Y/%m/%d")
    subject = f"📊 三大法人籌碼解析 - {report_date}"

    # 3. 產生 HTML 內容
    print("正在生成 HTML 報表...")
    html_content = generate_options_html(df, pc_df)

    # 4. 寄出信件
    return send_html_email(subject, html_content)


# ==========================================
# 測試區塊 (直接執行 send_email.py 時才會跑)
# ==========================================
if __name__ == "__main__":
    # # 測試 logic
    # print("測試 secrets_manager 整合...")
    # # 寄測試信給自己
    # my_creds = get_email_secrets()
    # send_html_email("Secrets Manager Test", "<h1>連線成功</h1>")
    # 測試從資料庫撈資料並產生報表
    print("--- 執行寄信整合測試 ---")
    send_daily_options_report()
