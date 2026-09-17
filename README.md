# 中文注音／點字轉換系統 — Chinese-to-Zhuyin & Braille Converter

> 將任意中文（含英文、數字、標點的混合文字）批次轉換為注音符號，並可進一步轉換為國家標準點字，
> 用於輔助視障學生的中文閱讀與學習教材製作。本專案為國科會（NSTC）研究計畫的技術產出之一。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-black)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)
![License](https://img.shields.io/badge/license-MIT-green)

## 專案背景

視障者的中文點字教材需要先將國字轉換為正確的注音，再依注音規則轉寫成點字，其中最大的技術難點是
**多音字判讀**：同一個漢字在不同語境下讀音不同（例如「重」在「重要」與「體重」中讀音不同），
單純查表無法正確處理。本專案結合固定注音對照表與 Gemini 大型語言模型的上下文理解能力，
在維持轉換準確度的同時控制 API 呼叫成本，作為國科會計畫中點字教材自動化產製流程的核心模組。

## 核心特點與技術亮點

- **多音字上下文判讀**：先以本地資料庫（10 萬餘筆國字/注音對照資料）判斷是否為多音字，
  只有多音字才會送交 Gemini API 依上下文決定正確讀音，非多音字直接查表，避免不必要的 API 呼叫
  （`backend/services/conversion_service.py:_convert_chinese_with_cache`）。
- **批次呼叫最佳化**：早期版本會依標點符號切段，每段各呼叫一次 Gemini API，短文章可能觸發
  10 次以上的 API 請求而超出頻率限制。改為「先掃描全文收集所有中文字、以 500 字為單位批次送出」後，
  同樣的文章可壓縮到 1–4 次呼叫（詳見 `CHANGELOG.md`），大幅降低延遲與被限流的風險
  （`backend/services/conversion_service.py:_batch_gemini_convert`）。
- **文字分段狀態機**：`_segment_text` 以字元類型（中文／英文／數字／中文標點／英文標點／空白）
  逐字掃描並合併相鄰同型字元，正確處理全形數字、多字元標點（如「……」）等邊界情況，
  是後續分流處理（查表、轉點字）的基礎。
- **完整的中文點字轉換規則引擎**：`braille_service.py` 實作聲母、介母、韻母、結合韻、聲調的點字對照，
  並處理數字加數符、英文字母加大寫符號等點字書寫慣例，而非僅做單一符號對應。
- **前後端解耦**：Flask 提供純 JSON API（`/api/convert`、`/api/braille`、`/api/health`），
  前端以原生 JavaScript 呼叫並支援 TXT 檔案上傳與結果下載，方便未來替換前端或整合進其他系統。

## 系統架構與技術棧

| 分類 | 技術 |
|---|---|
| 後端框架 | Python 3, Flask 3.0, Flask-CORS |
| AI 服務 | Google Gemini API（`gemini-2.5-flash`），用於多音字上下文判讀 |
| 資料庫 | MySQL 8.0（`pymysql`），儲存國字/注音對照表與使用者資料表 |
| 前端 | 原生 HTML / CSS / JavaScript（`frontend/bpmf.php`、`bpmf.css`） |
| 部署 | WSGI（`backend/wsgi.py`），Apache + mod_wsgi 或同等 WSGI 伺服器 |

```
前端 (bpmf.php)
   │  POST /api/convert  { text, include_braille }
   ▼
Flask API (zhuyin_routes.py)
   │
   ▼
ConversionService（文字分段 → 多音字判斷 → 批次 Gemini 查詢 → 點字轉換）
   │                              │
   ▼                              ▼
MySQL（zhuyin 對照表）      Gemini API（多音字上下文判讀）
```

## 專案架構目錄

```
chinese-zhuyin-converter/
├── backend/
│   ├── app.py                    # Flask app 建立與路由註冊
│   ├── config.py                 # 環境變數載入與設定管理
│   ├── wsgi.py                   # WSGI 進入點（正式環境部署用）
│   ├── requirements.txt
│   ├── .env.example              # 環境變數範本（複製為 .env 後填入實際值）
│   ├── routes/
│   │   └── zhuyin_routes.py      # /api/convert /api/braille /api/health
│   ├── services/
│   │   ├── conversion_service.py # 文字分段、多音字判斷、批次 Gemini 呼叫
│   │   ├── gemini_service.py     # Gemini API 封裝
│   │   └── braille_service.py    # 注音／數字／英文／標點 → 點字規則引擎
│   ├── database/
│   │   ├── db.py                 # MySQL 連線管理
│   │   └── init_db.py            # 建立資料庫與資料表
│   └── import_data/
│       ├── merged_zhuyin.csv     # 國字/注音對照原始資料（約 10.7 萬筆）
│       ├── import_merged_zhuyin_to_mysql.py
│       └── import_braille_to_mysql.py
├── frontend/
│   ├── bpmf.php                  # 主頁面（檔案上傳、轉換、下載）
│   └── bpmf.css
├── CHANGELOG.md                  # 開發過程重要優化紀錄
├── LICENSE
└── .gitignore
```

## 關鍵技術實作細節

### 1. 多音字批次判讀（`conversion_service.py`）

`convert_text` 的處理流程：先以 `_segment_text` 將輸入文字切成中文／英文／數字／標點段落，
再彙整所有中文字向 MySQL 做一次批次查詢（`_batch_get_char_info`），篩出其中的多音字。
只有多音字才會進入 `_batch_gemini_convert`，以 `BATCH_SIZE = 500` 字為單位分批呼叫 Gemini，
並保留原文上下文以提升判讀正確率；非多音字與批次結果最終統一在 `_convert_chinese_with_cache`
合併輸出。這個設計把「查表可解決的問題留給資料庫，只有真正需要語意判斷的才用 LLM」，
是控制 API 成本與延遲的關鍵。

### 2. 點字規則引擎（`braille_service.py`）

點字轉換並非單一符號對照，而是依聲母、介母、韻母、結合韻（如「ㄧㄢ」「ㄨㄥ」）、聲調
分別定義點字符號組合，並處理數字（`⠼` 數符前綴）、英文大寫（`⠠` 大寫符號前綴）等書寫慣例，
反映實際點字教材製作時需要遵守的轉寫規則，而不只是查表替換。

### 3. 資料庫設計（`database/init_db.py`）

`zhuyin` 表以 `hanzi`／`unicode_code`／`cns` 多欄位索引，`quantity` 欄位標示該字的注音數量，
供 `ConversionService` 快速判斷是否為多音字，是查表與 API 分流策略能成立的資料基礎。

## 量化成果與效能表現

- 國字/注音對照資料集規模：約 107,652 筆（`backend/import_data/merged_zhuyin.csv`）。
- 依 `CHANGELOG.md` 記錄的實測結果，批次處理優化前後的 Gemini API 呼叫次數對比：

  | 輸入規模 | 優化前 | 優化後 |
  |---|---|---|
  | 100 字文章（無標點） | 1 次 | 1 次 |
  | 100 字文章（10 個標點） | 最多 11 次 | 1 次 |
  | 1000 字文章 | 依標點數量而定 | 2 次 |
  | 2000 字文章 | 依標點數量而定 | 4 次 |

  優化重點是把 API 呼叫次數與「標點符號數量」解耦，改為與「總字數 / 500」成正比，
  在文章標點密集時效果最明顯。

## 快速開始

### 環境需求
- Python 3.10+
- MySQL 8.0（或相容版本）
- Google Gemini API 金鑰

### 安裝與設定
```bash
cd backend
pip install -r requirements.txt

# 複製環境變數範本並填入實際值
cp .env.example .env
# 編輯 .env：填入 GEMINI_API_KEY、DB_PASSWORD、SECRET_KEY 等
```

### 初始化資料庫
```bash
python database/init_db.py
python import_data/import_merged_zhuyin_to_mysql.py
python import_data/import_braille_to_mysql.py
```

### 本地執行
```bash
python app.py
```

Flask 會以 `frontend/` 作為靜態資源目錄提供 `bpmf.php` 頁面，並註冊 `/api/*` 路由。

### API 範例
```bash
curl -X POST http://localhost:5000/api/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，世界！", "include_braille": true}'
```

## 部署說明

正式環境透過 `backend/wsgi.py` 以 WSGI 介面（如 Apache + mod_wsgi）啟動，`create_app()` 由
`wsgi.py` 匯入並暴露為 `application`。實際部署過程中的伺服器位址、SSH/SCP 操作步驟與踩坑排解
記錄屬於維運資訊，未收錄於本 repo（原始專案資料夾中的部署筆記含內部伺服器位址，不適合公開）。

## 個人貢獻

本專案由本人獨立完成後端 API 設計（Flask 路由、多音字判讀流程、Gemini API 整合）、
點字轉換規則引擎，以及資料庫 schema 設計與資料匯入腳本；前端頁面與樣式亦由本人實作。

## 授權

本專案採用 [MIT License](LICENSE)。
