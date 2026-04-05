OptionsProject/
│
├── main.py                # 總調度程式 (Orchestrator)：負責執行流程
├── database.py            # 資料庫模組：封裝所有 Azure SQL 的 Insert/Query 邏輯
├── secrets_manager.py     # 金鑰管理員：負責從 .env 或 Azure Key Vault 抓取密碼
├── config.py              # 設定載入器：讀取 config/*.json 中的一般設定
├── logger.py              # 日誌記錄：負責記錄錯誤與執行狀態
├── utils.py               # 工具包：負責字串處理、日期轉換等重複邏輯
├── send_email.py          # 通知模組：負責寄發當日回報或報錯信件
│
├── scrapers/              # 爬蟲專區 (封裝各個爬蟲邏輯)
│   ├── __init__.py        # 讓資料夾變成一個 Package
│   ├── opt_contracts.py   # 抓取法人期權籌碼 (原本的 optContractsDate)
│   └── pc_ratio.py        # 抓取全市場 P/C Ratio
│
├── config/                # 設定檔資料夾
│   ├── settings.json      # 一般設定 (如：網址、資料表名稱)
│   └── .env               # 敏感設定 (密碼、Token) —— !!絕對不要進 Git!!
│
├── logs/                  # 執行紀錄資料夾 (自動產生)
│   └── scraper.log
│
├── .gitignore             # Git 排除清單：防止 .env 或 .vs 流出去
├── requirements.txt       # 套件清單：紀錄 pyodbc, requests, pandas 等
└── README.md              # 專案說明文件