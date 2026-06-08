如果目標是 **單機版 Windows 應用程式**，讓一般使用者安裝後即可使用，不需要架設 Web Server、PostgreSQL 或 Docker，那我會建議改採：

## 整體方案

### 技術架構

```text
┌─────────────────────────────┐
│ Windows Desktop Application │
│                             │
│ Python + PySide6            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ API執行引擎                 │
│ requests/httpx              │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ SQLite                      │
│ api_tool.db                 │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Excel Import/Export         │
│ pandas/openpyxl             │
└─────────────────────────────┘
```

---

# 系統定位

系統名稱：

**API批次查詢工具（API Batch Query Tool）**

用途：

```text
匯入Excel
↓
組合API參數
↓
批次呼叫API
↓
結果顯示Grid
↓
匯出Excel
```

類似：

* Postman（簡化版）
* ETL工具（簡化版）
* 政府開放資料查詢工具

---

# 開發工具

## Python

```text
Python 3.12
```

---

## GUI Framework

推薦：

```text
PySide6
```

原因：

* UI漂亮
* 免費
* 支援Table/Grid
* 支援Windows安裝檔

不建議：

```text
Tkinter
```

介面較老舊。

---

# 系統功能模組

## 主畫面

```text
┌───────────────────────────────────────────────┐
│ API批次查詢工具                               │
├───────────────────────────────────────────────┤
│ API設定                                       │
│ Excel匯入                                     │
│ 執行查詢                                      │
│ 查詢結果                                      │
└───────────────────────────────────────────────┘
```

---

# 模組1：API設定

## Form畫面

```text
API名稱：

[商工登記查詢]

API URL：

https://data.gcis.nat.gov.tw/od/data/api/v1/Rest/Opendata31

Method：

(GET ▼)

[儲存]
```

---

SQLite

```sql
api_master
```

```sql
CREATE TABLE api_master(
 id INTEGER PRIMARY KEY,
 api_name TEXT,
 api_url TEXT,
 method TEXT
);
```

---

# 模組2：API參數設定

畫面：

```text
┌─────────────────────────┐
│ API參數設定             │
├─────────────────────────┤
│參數名稱 │來源欄位│固定值│
├─────────────────────────┤
│Business_Accounting_NO│統編│ │
│$format│ │json│
└─────────────────────────┘

[新增]
[刪除]
```

---

SQLite

```sql
CREATE TABLE api_parameter(
 id INTEGER PRIMARY KEY,
 api_id INTEGER,
 parameter_name TEXT,
 source_column TEXT,
 default_value TEXT
);
```

---

# 模組3：Excel匯入

畫面

```text
[選擇Excel]

[載入]
```

---

使用

```python
pandas.read_excel()
```

---

載入後顯示

```text
QTableView
```

```text
┌────────────┐
│統編        │
├────────────┤
│24536806    │
│50869504    │
└────────────┘
```

---

# 模組4：欄位對應

自動抓Excel欄位

例如：

```text
Excel欄位：

統編
公司名稱
```

對應：

```text
Business_Accounting_NO ← 統編
```

---

畫面

```text
API參數            Excel欄位

Business_Accounting_NO  [統編 ▼]
```

---

# 模組5：API測試

按鈕

```text
[測試API]
```

---

系統組成：

```text
https://data.gcis.nat.gov.tw/
?
Business_Accounting_NO=24536806
```

---

顯示結果

```json
{
 "Company_Name":"測試公司"
}
```

---

# 模組6：批次執行

畫面

```text
總筆數：1000

成功：0

失敗：0

進度：

██████░░░░░░ 60%

[開始執行]
```

---

執行流程

```python
for row in excel_data:

    組API參數

    requests.get()

    解析JSON

    存SQLite

    更新ProgressBar
```

---

使用：

```python
QThread
```

避免畫面凍結。

---

# 模組7：結果顯示

主畫面

```text
┌────────────────────────────────────┐
│查詢結果                            │
├────────────────────────────────────┤
│統編 │公司名稱 │公司狀態 │地址      │
├────────────────────────────────────┤
│2453 │ABC公司 │核准設立 │台北市     │
└────────────────────────────────────┘
```

---

元件：

```python
QTableView
```

---

支援：

* 排序
* 搜尋
* 篩選

---

# 模組8：Excel匯出

按鈕

```text
[匯出Excel]
```

---

程式：

```python
df.to_excel(
    "result.xlsx",
    index=False
)
```

---

# SQLite資料表

## 查詢批次

```sql
CREATE TABLE batch_log(
 id INTEGER PRIMARY KEY,
 batch_no TEXT,
 execute_time DATETIME,
 total_count INTEGER,
 success_count INTEGER,
 fail_count INTEGER
);
```

---

## API結果

```sql
CREATE TABLE api_result(
 id INTEGER PRIMARY KEY,
 batch_no TEXT,
 request_data TEXT,
 response_data TEXT,
 create_time DATETIME
);
```

---

# 資料夾架構

```text
APIBatchTool/

├─ main.py

├─ ui/
│  ├─ main_window.py
│  ├─ api_setting.py
│  ├─ import_excel.py
│
├─ service/
│  ├─ api_service.py
│  ├─ excel_service.py
│  ├─ export_service.py
│
├─ db/
│  ├─ sqlite_service.py
│
├─ config/
│  ├─ setting.json
│
├─ database/
│  ├─ api_tool.db
│
└─ output/
```

---

# 打包成Windows安裝程式

## 第一步

使用

```bash
pip install pyinstaller
```

---

產生EXE

```bash
pyinstaller ^
--onefile ^
--windowed ^
main.py
```

產生：

```text
APIBatchTool.exe
```

---

## 第二步

製作安裝程式

使用：

* Inno Setup（推薦）
* NSIS

產出：

```text
APIBatchToolSetup.exe
```

使用者安裝後：

```text
C:\Program Files\APIBatchTool\
```

即可直接執行。

---

# 進階版（建議納入）

除了基本功能，再增加以下設計：

### API模板管理

例如：

* 商工登記
* 財政部統編
* 開放資料平台
* Google API

直接選擇模板即可使用。

---

### JSON欄位自動展開

例如：

```json
{
  "Company_Name":"ABC",
  "Address":"台北市"
}
```

自動產生欄位：

```text
Company_Name
Address
```

不需手動設定。

---

### 多執行緒查詢

```python
ThreadPoolExecutor
```

可同時查：

```text
10~50筆API
```

速度比逐筆查詢快數十倍。

---

### 查詢歷史

```text
批次編號
查詢時間
查詢筆數
成功筆數
```

可重新開啟查看結果。

---

### API Token管理

支援：

```text
API Key
Bearer Token
Basic Auth
```

適用於各種開放平台及企業API。

這樣的方案可完全採用 **Python + PySide6 + SQLite**，部署簡單、免安裝資料庫、可直接打包成 Windows 安裝程式，非常適合作為企業內部或稽核單位使用的 API 批次資料蒐集工具。
