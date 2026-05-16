import os
import io
import json
import urllib.parse
import pandas as pd
from database import DatabaseManager
from utils import get_date_with_weekday  # 引入 utils 的日期星期方法

def format_num(val):
    """處理金額格式，加上千分位，並將 NaN 轉為 0"""
    if pd.isna(val): return "0"
    return f"{int(val):,}"

def format_diff_html(val):
    """處理增減金額，加上正負號與括號，並自動判斷給予紅綠顏色"""
    if pd.isna(val) or val == 0: 
        return '<span class="diff-text" style="color: #666666;">(0)</span>'
    if val > 0: 
        return f'<span class="diff-text" style="color: red;">(+{int(val):,})</span>'
    return f'<span class="diff-text" style="color: green;">({int(val):,})</span>'

def generate_options_html(df, pc_df=None):
    """
    將 DataFrame 轉換為指定格式的 HTML 表格，包含期權籌碼數據、全市場 7 日籌碼趨勢和 P/C Ratio 曲線圖
    """
    if df is None or df.empty:
        return "<p>今日無期權籌碼資料。</p>"

    # 確保資料依日期反序排列 (最新的在最上面)
    df = df.sort_values(by=['Date', 'Item', 'CallPut'], ascending=[False, True, True])

    # 1. 取得報表最新日期 (格式如：2026/05/15 (五))
    raw_date = df['Date'].iloc[0]
    report_date = get_date_with_weekday(raw_date, format_str="%Y/%m/%d")

    # 取出最新一天的資料，用來產生三大法人的主表
    latest_df = df[df['Date'] == raw_date]

    # 2. 最新一天籌碼資料處理
    data_dict = {}
    for _, row in latest_df.iterrows():
        item = row['Item']
        cp = row['CallPut']
        if item not in data_dict:
            data_dict[item] = {}
        data_dict[item][cp] = row

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

    # --- 內部輔助函式：用來格式化趨勢表內的 C/P 值 ---
    def format_trend_cp(c_val, p_val):
        def format_val(v):
            if pd.isna(v) or v == 0: 
                return '<span style="color: #666666;">0</span>'
            color = "red" if v > 0 else "green"
            sign = "+" if v > 0 else ""
            return f'<span style="color: {color}; font-weight: bold;">{sign}{int(v):,}</span>'
        return f'<span style="color: #555;">C:</span> {format_val(c_val)}<br/><span style="color: #555;">P:</span> {format_val(p_val)}'

    # --- 3. 全市場期權籌碼解析 (近 7 日綜合趨勢表) ---
    trend_html = '<h3 style="margin-top: 30px; font-size: 16px; color: #6C6C6C; border-bottom: 2px solid #6C6C6C; padding-bottom: 5px;">全市場期權籌碼持倉追蹤 (近 7 日趨勢)</h3>'
    trend_html += '<table style="width: 100%; border-collapse: collapse; margin: 10px 0; background-color: #fff;">'
    trend_html += '<thead><tr style="background-color: #6C6C6C; color: white;">'
    trend_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">日期</th>'
    trend_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">外資 (C/P 淨額)</th>'
    trend_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">投信 (C/P 淨額)</th>'
    trend_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">自營商 (C/P 淨額)</th>'
    trend_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px; background-color: #555555; color: #fffde6;">散戶 (C/P 淨額)</th>'
    trend_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">大盤後市態度</th>'
    trend_html += '</tr></thead><tbody>'

    idx = 0
    for date_val, group in df.groupby('Date', sort=False):
        bg_color = '#f9f9f9' if idx % 2 == 0 else '#ffffff'
        idx += 1
        
        # 使用 utils 轉化日期格式，例如 "05/15 (五)"
        d_display = get_date_with_weekday(date_val, format_str="%m/%d")
        
        f_call = group[(group['Item'] == '外資') & (group['CallPut'] == 'CALL')]['淨額'].sum()
        f_put = group[(group['Item'] == '外資') & (group['CallPut'] == 'PUT')]['淨額'].sum()
        it_call = group[(group['Item'] == '投信') & (group['CallPut'] == 'CALL')]['淨額'].sum()
        it_put = group[(group['Item'] == '投信') & (group['CallPut'] == 'PUT')]['淨額'].sum()
        d_call = group[(group['Item'] == '自營商') & (group['CallPut'] == 'CALL')]['淨額'].sum()
        d_put = group[(group['Item'] == '自營商') & (group['CallPut'] == 'PUT')]['淨額'].sum()
        
        retail_call = -(f_call + it_call + d_call)
        retail_put = -(f_put + it_put + d_put)
        
        if retail_call < 0 and retail_put > 0:
            attitude = '<span style="color: red; font-weight: bold;">看漲 (散戶偏空，易軋空)</span>'
        elif retail_call > 0 and retail_put < 0:
            attitude = '<span style="color: green; font-weight: bold;">看跌 (散戶偏多，易殺多)</span>'
        elif retail_call > 0 and retail_put > 0:
            attitude = '<span style="color: #e6a23c; font-weight: bold;">震盪 (散戶雙買)</span>'
        elif retail_call < 0 and retail_put < 0:
            attitude = '<span style="color: #909399; font-weight: bold;">盤整 (散戶雙賣)</span>'
        else:
            attitude = '<span style="color: #6C6C6C;">中立</span>'

        trend_html += f'<tr style="background-color: {bg_color};">'
        trend_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px; font-weight: bold; color: #555;">{d_display}</td>'
        trend_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{format_trend_cp(f_call, f_put)}</td>'
        trend_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{format_trend_cp(it_call, it_put)}</td>'
        trend_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{format_trend_cp(d_call, d_put)}</td>'
        trend_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px; background-color: #fffdf0;">{format_trend_cp(retail_call, retail_put)}</td>'
        trend_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{attitude}</td>'
        trend_html += '</tr>'
        
    trend_html += '</tbody></table>'

    # --- 4. P/C Ratio 資料與 QuickChart 圖片生成 ---
    if pc_df is None or pc_df.empty:
        db = DatabaseManager()
        pc_df = db.fetch_put_call_ratio()
    
    pc_table_html = ""
    chart_url = ""
    
    if pc_df is not None and not pc_df.empty:
        pc_df = pc_df.copy()
        
        pc_df["PrevVolRatio"] = pc_df["PutCallVolumeRatio"].shift(1)
        pc_df["PrevOIRatio"] = pc_df["PutCallOIRatio"].shift(1)
        
        def get_pc_remark(current, prev):
            if pd.isna(prev):
                return '<span style="color: #999; font-size: 11px;">(無前日資料)</span>'
            diff = current - prev
            diff_abs = abs(diff)
            
            if prev < 100 and current >= 100:
                return f'<span style="color: red; font-size: 11px; font-weight: bold;">📈 增加 {diff_abs:.2f}%：反轉為 Put > Call</span>'
            if prev >= 100 and current < 100:
                return f'<span style="color: green; font-size: 11px; font-weight: bold;">📉 減少 {diff_abs:.2f}%：反轉為 Call > Put</span>'
                
            if current > 100:
                if diff > 0:
                    return f'<span style="color: red; font-size: 11px;">🔺 增加 {diff_abs:.2f}%：Put > Call 且佔比擴大</span>'
                elif diff < 0:
                    return f'<span style="color: green; font-size: 11px;">🔻 減少 {diff_abs:.2f}%：Put > Call 但 Call 佔比增加</span>'
                else:
                    return '<span style="color: #666; font-size: 11px;">➖ 無變動</span>'
            elif current < 100:
                if diff < 0:
                    return f'<span style="color: green; font-size: 11px;">🔻 減少 {diff_abs:.2f}%：Call > Put 且佔比擴大</span>'
                elif diff > 0:
                    return f'<span style="color: red; font-size: 11px;">🔺 增加 {diff_abs:.2f}%：Call > Put 但 Put 佔比增加</span>'
                else:
                    return '<span style="color: #666; font-size: 11px;">➖ 無變動</span>'
            else:
                return '<span style="color: #666; font-size: 11px;">➖ 持平 (100%)</span>'

        pc_table_html = '<table style="width: 100%; border-collapse: collapse; margin: 10px 0; background-color: #fff;">'
        pc_table_html += '<thead><tr style="background-color: #6C6C6C; color: white;">'
        pc_table_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">日期</th>'
        pc_table_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">賣權成交量</th>'
        pc_table_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">買權成交量</th>'
        pc_table_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px; background-color: #555555;">成交量比率及動態</th>'
        pc_table_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">賣權未平倉</th>'
        pc_table_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px;">買權未平倉</th>'
        pc_table_html += '<th style="padding: 10px; border: 1px solid #555; font-size: 12px; background-color: #555555;">未平倉比率及動態</th>'
        pc_table_html += '</tr></thead><tbody>'
        
        dates_list = []
        vol_ratio_list = []
        oi_ratio_list = []

        for idx_pc, (_, row) in enumerate(pc_df.iloc[::-1].iterrows()):
            bg_color = '#f9f9f9' if idx_pc % 2 == 0 else '#ffffff'
            
            # 使用 utils 轉化日期格式
            d_display = get_date_with_weekday(row['Date'], format_str="%m/%d")
            
            vol_remark = get_pc_remark(row["PutCallVolumeRatio"], row["PrevVolRatio"])
            oi_remark = get_pc_remark(row["PutCallOIRatio"], row["PrevOIRatio"])
            
            pc_table_html += f'<tr style="background-color: {bg_color};">'
            pc_table_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px; font-weight: bold; color: #555;">{d_display}</td>'
            pc_table_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{int(row["PutVolume"]):,}</td>'
            pc_table_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{int(row["CallVolume"]):,}</td>'
            pc_table_html += f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-size: 13px; font-weight: bold; color: #333;">{row["PutCallVolumeRatio"]:.2f}%<br/>{vol_remark}</td>'
            pc_table_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{int(row["PutOI"]):,}</td>'
            pc_table_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 12px;">{int(row["CallOI"]):,}</td>'
            pc_table_html += f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-size: 13px; font-weight: bold; color: #333;">{row["PutCallOIRatio"]:.2f}%<br/>{oi_remark}</td>'
            pc_table_html += '</tr>'
            
            # 折線圖 X 軸標籤同步套用帶星期的格式
            chart_label = get_date_with_weekday(row['Date'], format_str="%m/%d")
            dates_list.append(chart_label)
            vol_ratio_list.append(float(row["PutCallVolumeRatio"]))
            oi_ratio_list.append(float(row["PutCallOIRatio"]))
        
        pc_table_html += '</tbody></table>'
        
        dates_list.reverse()
        vol_ratio_list.reverse()
        oi_ratio_list.reverse()

        chart_config = {
            "type": "line",
            "data": {
                "labels": dates_list,
                "datasets": [
                    {
                        "label": "成交量比率 (%)",
                        "data": vol_ratio_list,
                        "borderColor": "#d9534f",
                        "backgroundColor": "rgba(217, 83, 79, 0.1)",
                        "fill": False,
                        "pointRadius": 4
                    },
                    {
                        "label": "未平倉比率 (%)",
                        "data": oi_ratio_list,
                        "borderColor": "#5cb85c",
                        "backgroundColor": "rgba(92, 184, 92, 0.1)",
                        "fill": False,
                        "pointRadius": 4
                    }
                ]
            },
            "options": {
                "title": {"display": False},
                "legend": {"position": "top"},
                "scales": {
                    "yAxes": [{"ticks": {"beginAtZero": True, "min": 0}}]
                }
            }
        }
        
        encoded_config = urllib.parse.quote(json.dumps(chart_config))
        chart_url = f"https://quickchart.io/chart?c={encoded_config}&w=600&h=300&bkg=white"

    else:
        pc_table_html = "<p style='text-align: center;'>無 P/C Ratio 資料</p>"

    # 5. HTML 模板總組合
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    body {{
        font-family: Arial, Helvetica, sans-serif;
        color: #333;
    }}
    .option-table {{
        width: 100%;
        border-collapse: collapse;
        background-color: #ffffff;
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
    .chart-container {{
        text-align: center;
        margin: 20px 0;
        background-color: #fff;
        padding: 10px;
        border: 1px solid #eee;
    }}
    </style>
    </head>
    <body>
    
    <h3 style="margin-top: 10px; font-size: 16px; color: #6C6C6C; border-bottom: 2px solid #6C6C6C; padding-bottom: 5px;">三大法人籌碼解析 {report_date}</h3>
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
    
    {trend_html}
    
    <h3 style="margin-top: 30px; font-size: 16px; color: #6C6C6C; border-bottom: 2px solid #6C6C6C; padding-bottom: 5px;">買賣權比率 (P/C Ratio) 趨勢與數據</h3>
    
    {f'<div class="chart-container"><img src="{chart_url}" alt="P/C Ratio Chart" style="max-width: 100%; height: auto;"></div>' if chart_url else ''}
    
    {pc_table_html}
    
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
        print("✅ 報表已產生！請打開 test_report.html 查看，程式碼結構已經成功精簡！")
    else:
        print("沒有資料可供產生報表。")