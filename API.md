# Clang-Tidy API 文件

本 API 提供靜態分析功能，讓出題者設定規則、自動生成 `.clang-tidy` 配置、執行檢查並儲存結果。

## 快速開始

```bash
# 1. 編譯模組（如果尚未編譯）
mkdir -p build && cd build
cmake .. && cmake --build . --config Release
cd ..

# 2. 安裝 Python 依賴
pip install -r requirements.txt

# 3. 啟動伺服器（FastAPI）
uvicorn api.app:app --host 0.0.0.0 --port 5000 --reload
# 或使用腳本（Linux/Mac）
./start_api.sh
```

伺服器會在 `http://localhost:5000` 啟動。

## API 端點總覽

| 方法 | 端點 | 說明 | 認證 |
|------|------|------|------|
| GET | `/health` | 健康檢查 | ❌ |
| POST | `/submission` | 建立提交 | ❌ |
| GET | `/submission/<id>` | 查詢提交 | ✅ |
| POST | `/lint/requirements` | 設定規則需求 | ✅ |
| POST | `/lint/generate` | 生成 .clang-tidy | ✅ |
| POST | `/lint/run` | 執行分析 | ❌ |
| POST | `/lint/report` | 儲存報告 | ✅ |

## 詳細說明

### 1. GET `/submission/<submission>` – 取得提交程式碼

**用途：** 取得指定提交的原始碼。

**請求：**
- 路徑參數：`submission` (int)
- 標頭：`Authorization: Bearer <token>`

**回應範例：**
```json
{
  "submission_id": 123,
  "problem_id": 456,
  "code": "int main() { ... }",
  "language": "cpp",
  "created_at": "2025-11-16T10:30:00"
}
```

**錯誤：**
- 401: 未認證
- 403: 權限不足
- 404: 提交不存在

---

### 2. POST `/lint/requirements` – 提交規則需求

**用途：** 由出題者設定靜態分析規則。

**請求：**
```json
{
  "problem_id": 456,
  "rules": [
    "--forbid-loops",
    "--forbid-arrays",
    "--forbid-functions=printf,scanf",
    "--forbid-stl"
  ]
}
```

**規則選項：**
- `--forbid-loops`: 禁用迴圈
- `--forbid-arrays`: 禁用陣列
- `--forbid-stl`: 禁用 STL
- `--forbid-functions=func1,func2`: 禁用特定函式

**回應範例：**
```json
{
  "message": "requirements saved.",
  "config_id": "cfg_456"
}
```

---

### 3. POST `/lint/generate` – 生成配置檔

**用途：** 根據規則自動生成 `.clang-tidy`。

**請求：**
```json
{
  "problem_id": 456,
  "rules": ["--forbid-loops", "--forbid-stl"],
  "language_type": 1
}
```
- `language_type`: 0=C, 1=C++（可選）

**回應範例：**
```json
{
  "message": "Generated .clang-tidy for problem 456",
  "config_path": "/path/to/configs/problem_456/.clang-tidy",
  "config_content": "Checks: misc-forbid-loops,misc-forbid-stl\nWarningsAsErrors: '*'"
}
```

---

### 4. POST `/lint/run` – 執行檢查

**用途：** 對提交執行 Clang-Tidy 分析。

**請求：**
```json
{
  "submission_id": 123,
  "problem_id": 456,
  "language_type": 1,
  "timeout_sec": 30,
  "export_fixes": true
}
```

**回應範例：**
```json
{
  "message": "clang-tidy completed.",
  "run_id": "run_123_1700000000",
  "status": "finished",
  "violations_count": 3,
  "fixes_available": true
}
```

**狀態值：**
- `running`: 執行中
- `finished`: 完成
- `failed`: 失敗

---

### 5. POST `/lint/report` – 儲存報告

**用途：** 將分析結果存入資料庫。

**請求：**
```json
{
  "submission_id": 123,
  "problem_id": 456,
  "run_id": "run_xyz",
  "result": {
    "passed": false,
    "violations": [
      {
        "rule": "misc-forbid-loops",
        "message": "Loop statements are forbidden.",
        "file": "code.cpp",
        "line": 10,
        "column": 5
      }
    ],
    "total_violations": 3,
    "execution_time_ms": 245
  }
}
```

**回應範例：**
```json
{
  "message": "report saved.",
  "report_id": "rpt_123_1700000000"
}
```

---

## 完整使用流程

### 場景：出題者設定題目規則並檢查學生提交

```bash
# 1. 出題者設定規則
curl -X POST http://localhost:5000/lint/requirements \
  -H "Authorization: Bearer token123" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "rules": ["--forbid-loops", "--forbid-stl"]
  }'

# 2. 生成配置檔
curl -X POST http://localhost:5000/lint/generate \
  -H "Authorization: Bearer token123" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "rules": ["--forbid-loops", "--forbid-stl"]
  }'

# 3. 學生提交程式碼
curl -X POST http://localhost:5000/submission \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "code": "#include <iostream>\nint main() { return 0; }",
    "language": "cpp"
  }'

# 4. 執行靜態分析
curl -X POST http://localhost:5000/lint/run \
  -H "Content-Type: application/json" \
  -d '{
    "submission_id": 1,
    "problem_id": 1,
    "language_type": 1
  }'

# 5. 儲存分析報告
curl -X POST http://localhost:5000/lint/report \
  -H "Authorization: Bearer token123" \
  -H "Content-Type: application/json" \
  -d '{
    "submission_id": 1,
    "problem_id": 1,
    "run_id": "run_1_xxx",
    "result": { ... }
  }'
```

## 使用測試腳本

提供了完整的測試腳本：

```bash
python api/test_api.py
```

測試腳本會自動執行完整流程：
1. 健康檢查
2. 建立測試提交
3. 設定規則需求
4. 生成配置檔
5. 執行分析
6. 儲存報告
7. 查詢提交

## 資料庫結構

使用 SQLite 資料庫 (`api/database.db`)：

### submissions 表
```sql
CREATE TABLE submissions (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    language TEXT NOT NULL,
    created_at TEXT NOT NULL,
    user_id INTEGER
);
```

### requirements 表
```sql
CREATE TABLE requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL UNIQUE,
    rules TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### lint_runs 表
```sql
CREATE TABLE lint_runs (
    id TEXT PRIMARY KEY,
    submission_id INTEGER NOT NULL,
    problem_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    violations_count INTEGER,
    fixes_available BOOLEAN,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error_message TEXT
);
```

### lint_reports 表
```sql
CREATE TABLE lint_reports (
    id TEXT PRIMARY KEY,
    submission_id INTEGER NOT NULL,
    problem_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    violations TEXT NOT NULL,
    total_violations INTEGER NOT NULL,
    execution_time_ms INTEGER,
    created_at TEXT NOT NULL
);
```

## 錯誤處理

| 狀態碼 | 說明 |
|--------|------|
| 200 | 成功 |
| 201 | 建立成功 |
| 400 | 請求參數錯誤 |
| 401 | 未認證 |
| 403 | 權限不足 |
| 404 | 資源不存在 |
| 500 | 伺服器錯誤 |

## 部署建議

### 開發環境
```bash
uvicorn api.app:app --host 0.0.0.0 --port 5000 --reload
```

### 生產環境（Gunicorn + Uvicorn workers）
```bash
pip install gunicorn uvicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000 api.app:app
```

### Docker
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    clang-tidy llvm cmake build-essential

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN mkdir -p build && cd build && cmake .. && cmake --build .

EXPOSE 5000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "5000"]
```

## 安全性

當前實作為示範版本，生產環境需要：
1. 實作真實的 JWT/OAuth2 認證
2. 使用者權限管理系統
3. 輸入驗證與清理
4. Rate limiting
5. HTTPS/TLS
6. 使用 Docker/isolate 隔離執行環境
7. 資源限制（CPU/記憶體/執行時間）

## 故障排除

詳見 `api/README.md`。

## 授權

與主專案相同。
