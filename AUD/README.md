# Internal Audit Management System

依據 `AUD/ICP.MD` 建立的 FastAPI MVP，包含：

- JWT 登入驗證與角色欄位
- 用戶新增與維護
- 年度稽核計畫 CRUD
- 年度稽核計畫 Excel 匯出/匯入
- 稽核題庫 CRUD 與查詢
- 稽核題庫 Excel 匯出/匯入
- 稽核查核記錄 CRUD
- 查核記錄依稽核任務維護與 Excel 匯出/匯入
- CAR/OFI/OBS 改善追蹤 CRUD
- 首頁公告與 Dashboard 統計 API
- Bootstrap 單頁前端原型

## 快速啟動

```powershell
cd D:\Project\AUD
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

開啟：

```text
http://127.0.0.1:8000
```

預設會使用本機 SQLite：`sqlite:///./iams_dev.db`。若要使用 PostgreSQL，先啟動資料庫：

```powershell
docker compose up -d
$env:DATABASE_URL="postgresql+psycopg://iams_user:iams_password@localhost:5432/iams"
uvicorn app.main:app --reload
```

## 預設帳號

啟動時會自動建立管理者帳號：

- 帳號：`admin`
- 密碼：`admin123`

正式環境請登入後立即更換密碼，並設定 `JWT_SECRET_KEY`。
