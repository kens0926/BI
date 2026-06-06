# API 批次查詢工具

這個專案是依照 `UI_API.MD` 的設計開始開發的 Windows 桌面 API 批次查詢工具。

## 功能

- API 設定
- API 設定儲存與管理
- Excel 匯入與資料預覽
- API 參數對應設定
- API 測試呼叫
- 批次 API 查詢
- 查詢結果顯示與匯出

## 安裝與執行

1. 建議建立 Python 虛擬環境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. 安裝依賴

```bash
python -m pip install -r requirements.txt
```

3. 執行應用程式

```bash
python main.py
```

## 注意

- 目前支援 `GET` 與 `POST` API
- Excel 讀取依賴 `pandas` 與 `openpyxl`
- 目前尚未包裝成安裝檔，先以 Python 直行版本開發
