# Clang-Tidy API Server (FastAPI)

基於 FastAPI 的 Clang-Tidy 靜態分析 API 伺服器。

## 快速開始

### 1. 安裝依賴

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# 確保已編譯 clang-tidy 模組
cd build
cmake .. && cmake --build . --config Release
cd ..
```

### 2. 啟動伺服器

```bash
uvicorn api.app:app --host 0.0.0.0 --port 5000 --reload
```

伺服器會在 `http://localhost:5000` 啟動（支援自動重載）。

### 3. 測試 API

```bash
# 在另一個終端執行測試
python api/test_api.py
```

## API 端點

### 1. 健康檢查
```bash
curl http://localhost:5000/health
```

### 2. 建立提交
```bash
curl -X POST http://localhost:5000/submission \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "code": "#include <iostream>\nint main() { return 0; }",
    "language": "cpp"
  }'
```

### 3. 設定規則需求
```bash
curl -X POST http://localhost:5000/lint/requirements \
  -H "Authorization: Bearer test_token" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "rules": ["--forbid-loops", "--forbid-stl"]
  }'
```

### 4. 生成配置
```bash
curl -X POST http://localhost:5000/lint/generate \
  -H "Authorization: Bearer test_token" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1,
    "rules": ["--forbid-loops", "--forbid-stl"],
    "language_type": 1
  }'
```

### 5. 執行分析
```bash
curl -X POST http://localhost:5000/lint/run \
  -H "Content-Type: application/json" \
  -d '{
    "submission_id": 1,
    "problem_id": 1,
    "language_type": 1,
    "export_fixes": true
  }'
```

### 6. 儲存報告
```bash
curl -X POST http://localhost:5000/lint/report \
  -H "Authorization: Bearer test_token" \
  -H "Content-Type: application/json" \
  -d '{
    "submission_id": 1,
    "problem_id": 1,
    "run_id": "run_123",
    "result": {
      "passed": false,
      "violations": [...],
      "total_violations": 3
    }
  }'
```

### 7. 查詢提交
```bash
curl http://localhost:5000/submission/1 \
  -H "Authorization: Bearer test_token"
```

## 資料庫結構

SQLite 資料庫 (`api/database.db`) 包含以下表：

- `submissions`: 儲存使用者提交
- `requirements`: 儲存題目規則需求
- `lint_runs`: 儲存分析執行記錄
- `lint_reports`: 儲存分析報告

## 配置

在 `app.py` 中可修改以下設定：

```python
BASE_DIR = Path(__file__).parent.parent
BUILD_DIR = BASE_DIR / "build"
MODULE_PATH = BUILD_DIR / "libMiscTidyModule.so"
SCRIPT_PATH = BASE_DIR / "scripts" / "generate_tidy_config.py"
CONFIG_DIR = BASE_DIR / "configs"
DB_PATH = BASE_DIR / "api" / "database.db"
```

## 部署建議

### 使用 Gunicorn（Uvicorn workers）

```bash
pip install gunicorn uvicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000 api.app:app
```


## 安全性注意事項

1. **認證**: 當前使用簡單的 Bearer token，生產環境應整合 JWT 或 OAuth2
2. **權限控制**: 需實作真實的使用者權限系統
3. **輸入驗證**: 對所有輸入進行嚴格驗證
4. **沙箱隔離**: 使用 Docker 或 isolate 隔離 clang-tidy 執行
5. **資源限制**: 設定 timeout 和記憶體限制
6. **HTTPS**: 生產環境必須使用 HTTPS

## 故障排除

### clang-tidy 找不到模組
```bash
# 檢查模組是否存在
ls -l build/libMiscTidyModule.so

# 重新編譯
cd build && cmake --build . --config Release
```

### 資料庫錯誤
```bash
# 刪除並重建資料庫
rm -f api/database.db
uvicorn api.app:app --port 5000  # 啟動時會自動初始化
```

### Python 依賴問題
```bash
# 使用虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 開發

### 執行測試
```bash
python api/test_api.py
```

### 啟用 Debug 模式
```python
# 在 app.py 最後一行
app.run(host='0.0.0.0', port=5000, debug=True)
```

### 查看日誌
```bash
# ASGI 伺服器會將日誌輸出到 stdout
uvicorn api.app:app --port 5000 2>&1 | tee api.log
```

## 授權

與主專案相同。
