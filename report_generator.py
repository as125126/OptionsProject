import os

import pandas as pd
from database import DatabaseManager

def format_num(val):
    """處理金額格式，加上千分位，並將 NaN 轉為 0"""
    if pd.isna(val): return "0"
    return f"{int(val):,}"

def format_diff_html(val):
    """處理增減金額，加上正負號與括號，並自動判斷給予紅綠顏色"""
    if pd.isna(val) or val == 0: 
        return '<span class="diff-text" style="color: #666666;">(0)</span>'  # 灰色代表無變動
    if val > 0: 
        return f'<span class="diff-text" style="color: red;">(+{int(val):,})</span>'  # 正數為紅色
    return f'<span class="diff-text" style="color: green;">({int(val):,})</span>'  # 負數為綠色 (負數自帶 - 號)

def generate_options_html(df):
    """
    將 DataFrame 轉換為指定格式的 HTML 表格
    """
    if df is None or df.empty:
        return "<p>今日無期權籌碼資料。</p>"

    # 1. 取得報表日期並格式化為 MM/DD
    raw_date = df['Date'].iloc[0]
    if isinstance(raw_date, str):
        report_date = pd.to_datetime(raw_date).strftime('%Y/%m/%d')
    else:
        report_date = raw_date.strftime('%Y/%m/%d')

    # 2. 將 DataFrame 轉換為嵌套字典
    data_dict = {}
    for _, row in df.iterrows():
        item = row['Item']
        cp = row['CallPut']
        if item not in data_dict:
            data_dict[item] = {}
        data_dict[item][cp] = row

    # 輔助取值函數
    def get_val(item, cp, col):
        try:
            return format_num(data_dict[item][cp][col])
        except KeyError:
            return "0"

    def get_diff(item, cp, col):
        try:
            return format_diff_html(data_dict[item][cp][col])
        except KeyError:
            return '<span class="diff-text" style="color: #999999;">(0)</span>'

    # 3. HTML 模板 (已更新為 6C6C6C 灰階主題)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    .option-table {{
        width: 100%;
        border-collapse: collapse;
        background-color: #ffffff;
        font-family: Arial, Helvetica, sans-serif;
    }}
    .option-table thead {{
        background-color: #6C6C6C;
        color: white;
    }}
    .option-table thead th {{
        padding: 12px;
        text-align: center;
        font-weight: bold;
        font-size: 13px;
        border: 1px solid #555555;
    }}
    .option-table tbody td {{
        padding: 10px;
        text-align: center;
        font-size: 13px;
        border: 1px solid #ddd;
        color: #333;
    }}
    .option-table tbody tr:nth-child(even) {{
        background-color: #f9f9f9;
    }}
    .option-table td:first-child {{
        background-color: #f2f2f2;
        font-weight: bold;
        color: #6C6C6C;
        width: 50px;
    }}
    .diff-text {{
        font-size: 11px;
        font-weight: bold;
    }}
    </style>
    </head>
    <body>
    <table class="option-table">
        <thead>
            <tr>
                <th rowspan="2">{report_date}</th>
                <th colspan="3">外資</th>
                <th colspan="3">投信</th>
                <th colspan="3">自營商</th>
            </tr>
            <tr>
                <th>買方</th>
                <th>賣方</th>
                <th>買賣差額</th>
                <th>買方</th>
                <th>賣方</th>
                <th>買賣差額</th>
                <th>買方</th>
                <th>賣方</th>
                <th>買賣差額</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>買權</td>
                <td><span>{get_val('外資', 'CALL', '買方')}</span><br/>{get_diff('外資', 'CALL', '買方增減')}</td>
                <td><span>{get_val('外資', 'CALL', '賣方')}</span><br/>{get_diff('外資', 'CALL', '賣方增減')}</td>
                <td>{get_val('外資', 'CALL', '淨額')}</td>
                
                <td><span>{get_val('投信', 'CALL', '買方')}</span><br/>{get_diff('投信', 'CALL', '買方增減')}</td>
                <td><span>{get_val('投信', 'CALL', '賣方')}</span><br/>{get_diff('投信', 'CALL', '賣方增減')}</td>
                <td>{get_val('投信', 'CALL', '淨額')}</td>
                
                <td><span>{get_val('自營商', 'CALL', '買方')}</span><br/>{get_diff('自營商', 'CALL', '買方增減')}</td>
                <td><span>{get_val('自營商', 'CALL', '賣方')}</span><br/>{get_diff('自營商', 'CALL', '賣方增減')}</td>
                <td>{get_val('自營商', 'CALL', '淨額')}</td>
            </tr>
            <tr>
                <td>賣權</td>
                <td><span>{get_val('外資', 'PUT', '買方')}</span><br/>{get_diff('外資', 'PUT', '買方增減')}</td>
                <td><span>{get_val('外資', 'PUT', '賣方')}</span><br/>{get_diff('外資', 'PUT', '賣方增減')}</td>
                <td>{get_val('外資', 'PUT', '淨額')}</td>
                
                <td><span>{get_val('投信', 'PUT', '買方')}</span><br/>{get_diff('投信', 'PUT', '買方增減')}</td>
                <td><span>{get_val('投信', 'PUT', '賣方')}</span><br/>{get_diff('投信', 'PUT', '賣方增減')}</td>
                <td>{get_val('投信', 'PUT', '淨額')}</td>
                
                <td><span>{get_val('自營商', 'PUT', '買方')}</span><br/>{get_diff('自營商', 'PUT', '買方增減')}</td>
                <td><span>{get_val('自營商', 'PUT', '賣方')}</span><br/>{get_diff('自營商', 'PUT', '賣方增減')}</td>
                <td>{get_val('自營商', 'PUT', '淨額')}</td>
            </tr>
        </tbody>
    </table>
    </body>
    </html>
    """
    return html_template

if __name__ == "__main__":
    db = DatabaseManager()
    print("--- 測試從資料庫撈取資料 ---")
    df = db.fetch_latest_options_data()
    
    if not df.empty:

        export_dir = "export"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        file_path = os.path.join(export_dir, "test_report.html")

        print("\n--- 產生 HTML 報表 ---")
        html_output = generate_options_html(df)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_output)
        print("✅ 報表已產生！請打開 test_report.html 查看。")
    else:
        print("沒有資料可供產生報表。")