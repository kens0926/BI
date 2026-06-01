以下整理為較正式的「系統開發規格書」架構，已依照你指定的技術方向：

* 程式語言：Python
* 資料庫：PostgreSQL

內容會偏向資深系統分析／系統設計文件格式，可直接作為後續：

* 系統分析
* 軟體開發
* 專案估工
* UI設計
* API設計
* 資料庫建模
  的基礎。

# 內控稽核管理系統（Internal Audit Management System）

# 系統開發規格書

---

# 1. 系統概要

## 1.1 系統名稱

內控稽核管理系統（Internal Audit Management System, IAMS）

---

## 1.2 系統目的

建置一套企業內部控制稽核管理平台，協助稽核部門進行：

* 年度稽核規劃
* 稽核任務管理
* 稽核題庫管理
* 查核結果記錄
* 缺失改善追蹤
* 稽核資料保存與分析

藉由系統化流程，提高稽核效率、標準化作業流程與強化管理追蹤能力。

---

# 2. 系統架構

## 2.1 系統架構模式

採用三層式 Web 架構（3-Tier Architecture）

### 架構分層

1. Presentation Layer（前端介面）
2. Application Layer（後端服務）
3. Database Layer（資料庫）

---

## 2.2 技術架構

| 項目         | 技術                             |
| ---------- | ------------------------------ |
| 前端         | HTML5 / Bootstrap / JavaScript |
| 後端         | Python FastAPI                 |
| ORM        | SQLAlchemy                     |
| API格式      | RESTful API                    |
| 資料庫        | PostgreSQL                     |
| 驗證機制       | JWT Token                      |
| 檔案儲存       | Local Storage / NAS            |
| 部署環境       | Linux Server                   |
| Web Server | Nginx                          |
| 容器化        | Docker（建議）                     |

---

# 3. 系統功能模組

---

# 3.1 首頁公告模組

## 功能說明

提供系統登入後首頁資訊展示。

## 功能需求

### 公告管理

* 建立公告
* 修改公告
* 公告上下架
* 置頂公告

### 首頁資訊

* 顯示待執行稽核任務
* 顯示近期稽核進度
* 顯示缺失改善待追蹤項目

---

# 3.2 年度稽核規劃模組

## 功能說明

建立年度稽核計畫與管理稽核任務。

---

## 功能需求

### 年度計畫建立

* 建立年度計畫
* 指定年度
* 建立九大循環稽核任務

### 稽核任務管理

欄位如下：

| 欄位    | 型態        |
| ----- | --------- |
| 任務編號  | VARCHAR   |
| 稽核年度  | INTEGER   |
| 稽核循環  | VARCHAR   |
| 被稽核部門 | VARCHAR   |
| 稽核員   | VARCHAR   |
| 開始日期  | DATE      |
| 結束日期  | DATE      |
| 任務狀態  | VARCHAR   |
| 建立時間  | TIMESTAMP |

---

## 任務狀態

* Draft
* Pending
* In Progress
* Completed
* Closed

---

# 3.3 稽核題庫管理模組

## 功能說明

建立標準化稽核題庫。

---

## 功能需求

### 題庫管理

* 新增題目
* 修改題目
* 停用題目
* 分類管理

### 題庫匯入

* 支援 Excel 匯入
* 提供匯入範本

### 題庫查詢

* 關鍵字搜尋
* 循環分類查詢
* 部門查詢

---

## 題庫資料欄位

| 欄位   | 型態        |
| ---- | --------- |
| 題目ID | UUID      |
| 稽核循環 | VARCHAR   |
| 題目內容 | TEXT      |
| 查核程序 | TEXT      |
| 風險說明 | TEXT      |
| 法規依據 | TEXT      |
| 適用部門 | VARCHAR   |
| 啟用狀態 | BOOLEAN   |
| 建立時間 | TIMESTAMP |

---

# 3.4 稽核執行模組

## 功能說明

執行實際稽核作業。

---

## 功能需求

### 建立稽核工作底稿

* 從題庫勾選題目
* 可新增臨時題目
* 產生本次稽核工作清單

### 查核記錄

每題需記錄：

| 欄位     | 型態        |
| ------ | --------- |
| 查核結果ID | UUID      |
| 任務ID   | UUID      |
| 題目ID   | UUID      |
| 查核結果   | VARCHAR   |
| 查核說明   | TEXT      |
| 改善建議   | TEXT      |
| 附件路徑   | VARCHAR   |
| 建立者    | VARCHAR   |
| 建立時間   | TIMESTAMP |

---

## 查核結果類型

| 類型   | 說明                          |
| ---- | --------------------------- |
| CAR  | Corrective Action Request   |
| OFI  | Opportunity For Improvement |
| OBS  | Observation                 |
| NA   | Not Applicable              |
| PASS | 符合                          |

---

# 3.5 缺失改善追蹤模組

## 功能說明

追蹤CAR改善進度。

---

## 功能需求

### 缺失追蹤

* 指派責任單位
* 設定改善期限
* 上傳改善證據
* 改善狀態更新

---

## 改善狀態

* Open
* Processing
* Pending Verify
* Closed

---

# 3.6 報表模組

## 功能說明

產出稽核相關報表。

---

## 報表類型

### 稽核報告

* 稽核摘要
* 查核結果
* CAR清單
* OFI清單

### 統計分析

* 各部門缺失統計
* CAR趨勢分析
* 高風險項目分析

---

# 4. 權限管理

## 4.1 角色定義

| 角色              | 權限     |
| --------------- | ------ |
| Admin           | 系統管理   |
| Audit Manager   | 年度計畫管理 |
| Auditor         | 稽核執行   |
| Department User | 改善回覆   |
| Viewer          | 查詢     |

---

## 4.2 驗證方式

採用 JWT Authentication。

---

# 5. 資料庫設計（PostgreSQL）

---

# 5.1 users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    account VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    role VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

# 5.2 audit_plans

```sql
CREATE TABLE audit_plans (
    id UUID PRIMARY KEY,
    year INTEGER NOT NULL,
    cycle_name VARCHAR(100),
    department VARCHAR(100),
    auditor_id UUID,
    start_date DATE,
    end_date DATE,
    status VARCHAR(30),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

# 5.3 audit_question_bank

```sql
CREATE TABLE audit_question_bank (
    id UUID PRIMARY KEY,
    cycle_name VARCHAR(100),
    question TEXT,
    procedure TEXT,
    risk_description TEXT,
    regulation_reference TEXT,
    department VARCHAR(100),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

# 5.4 audit_records

```sql
CREATE TABLE audit_records (
    id UUID PRIMARY KEY,
    audit_plan_id UUID,
    question_id UUID,
    result_type VARCHAR(20),
    finding TEXT,
    suggestion TEXT,
    attachment_path VARCHAR(255),
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

# 5.5 corrective_actions

```sql
CREATE TABLE corrective_actions (
    id UUID PRIMARY KEY,
    audit_record_id UUID,
    responsible_department VARCHAR(100),
    due_date DATE,
    action_description TEXT,
    status VARCHAR(30),
    verified_by UUID,
    verified_at TIMESTAMP
);
```

---

# 6. API設計規範

---

# 6.1 API命名規則

採 RESTful API：

| Method | URL                   | 說明     |
| ------ | --------------------- | ------ |
| GET    | /api/audit-plans      | 查詢年度計畫 |
| POST   | /api/audit-plans      | 建立年度計畫 |
| PUT    | /api/audit-plans/{id} | 更新計畫   |
| DELETE | /api/audit-plans/{id} | 刪除計畫   |

---

# 6.2 API回應格式

```json
{
  "success": true,
  "message": "Data retrieved successfully",
  "data": []
}
```

---

# 7. 非功能需求

---

# 7.1 效能需求

* 同時上線人數：100 Users
* API Response Time < 3 秒
* 支援大型Excel匯入

---

# 7.2 安全需求

* JWT Token 驗證
* Password Hashing
* Role-Based Access Control
* SQL Injection 防護
* API Rate Limit

---

# 7.3 備份需求

* PostgreSQL 每日備份
* 附件檔案定期備份

---

# 8. 系統流程

---

# 8.1 年度稽核流程

1. 建立年度稽核計畫
2. 指派稽核員
3. 建立稽核工作底稿
4. 執行稽核
5. 記錄查核結果
6. 建立CAR
7. 改善追蹤
8. 結案

---

# 9. 未來擴充建議

## Phase 2

* Email通知
* LDAP整合
* Power BI Dashboard
* 行動裝置支援
* 電子簽核流程

## Phase 3

* AI風險分析
* AI稽核題目推薦
* OCR附件辨識
* 稽核知識庫

---

# 10. 開發建議

## 開發方式

採 Agile Sprint 開發。

---

## 建議開發順序

### MVP版本

1. 使用者登入
2. 年度計畫
3. 題庫管理
4. 稽核執行
5. 查核記錄

### 第二階段

1. CAR追蹤
2. 報表
3. Dashboard

### 第三階段

1. AI功能
2. BI分析
3. 通知整合
