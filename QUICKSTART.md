# 快速開始

## 1. 編譯模組

### Linux / macOS / WSL
```bash
mkdir -p build && cd build
cmake ..
cmake --build . --config Release
```

### Windows (PowerShell + MSVC)
```powershell
mkdir build; cd build
cmake ..
cmake --build . --config Release
```

## 2. 測試範例

### Linux / macOS / WSL
```bash
./scripts/test_examples.sh
```

### Windows (PowerShell)
```powershell
.\scripts\test_examples.ps1
```

## 3. 手動執行單一檢查

### Linux / macOS / WSL
```bash
clang-tidy examples/main.c \
  -load ./build/libMiscTidyModule.so \
  -checks='misc-forbid-arrays' \
  -- -std=c17
```

### Windows (PowerShell)
```powershell
clang-tidy examples\main.c `
  -load .\build\MiscTidyModule.dll `
  -checks='misc-forbid-arrays' `
  -- -std=c17
```

## 4. 自動產生 .clang-tidy

```bash
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays
```

產生的 `.clang-tidy` 會包含指定的檢查規則。

## 可用的檢查規則

- `misc-forbid-loops` — 禁止 for/while/do-while
- `misc-forbid-arrays` — 禁止陣列宣告
- `misc-forbid-functions` — 禁止特定函式（可透過 CheckOptions 設定）

## 設定禁用函式清單

在 `.clang-tidy` 中：

```yaml
CheckOptions:
  - key: misc-forbid-functions.ForbiddenNames
    value: 'sort,printf,malloc,free'
```

詳細說明請見 `README.md`。
