OptionsProject/
│
├── main.py                # 總調度程式 (Orchestrator)：負責串接爬蟲、資料庫與通知流程
├── database.py            # 資料庫模組：封裝 SQL Server / Azure SQL 的連線與 CRUD 邏輯
├── secrets_manager.py     # 金鑰管理員：負責從 .env 或環境變數安全抓取敏感密碼
├── config.py              # 設定載入器：負責讀取並解析 config/*.json 中的環境設定
├── logger.py              # 日誌記錄：負責記錄系統執行狀態、成功訊息與 Error Log
├── report_generator.py    # 生產器：Email格式處理
├── send_email.py          # 通知模組：當執行完畢或發生異常時，自動寄送郵件回報
│
├── scrapers/              # 爬蟲模組資料夾
│   ├── __init__.py        # 將資料夾標記為 Python Package
│   ├── opt_contracts.py   # 核心爬蟲：抓取三大法人期權部位 (Institutional Options)
│   └── pc_ratio.py        # 核心爬蟲：抓取全市場 Put/Call Ratio
│
├── config/                # 設定檔資料夾
│   ├── settings.json      # 一般設定：存放 URL、資料表名稱、重試次數等非敏感資訊
│   └── .env               # 敏感設定：存放資料庫密碼、API Token（！！嚴禁進入 Git 追蹤！！）
│
├── logs/                  # 日誌資料夾 (自動產生)
│   └── scraper.log        # 紀錄程式執行的歷史細節
│
├── .gitignore             # Git 排除清單：防止敏感檔案 (如 .env, .venv) 流入版本控制
├── requirements.txt       # 套件依賴清單：記錄專案所需套件 (pyodbc, pandas, requests 等)
└── README.md              # 專案說明文件：即本檔案