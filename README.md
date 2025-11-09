
本專案提供一組簡單的 clang-tidy 自訂規則（module），用於 Online Judge（OJ）在批改階段進行靜態分析，例如禁止迴圈、禁止陣列、或禁止特定函式的使用。

## 快速開始

```bash
# 1. 編譯模組（在 WSL/Linux 環境）
mkdir -p build && cd build
cmake .. && cmake --build . --config Release
cd ..

# 2. 生成配置（例如：禁用迴圈和陣列）
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays

# 3. 執行檢查
clang-tidy your_code.c \
    -load ./build/libMiscTidyModule.so \
    -export-fixes=fixes.yaml \
    -- -std=c17

# 4. 查看結果
cat fixes.yaml
```

## 主要功能

- 禁用迴圈（`misc-forbid-loops`）：for / while / do-while
- 禁用陣列（`misc-forbid-arrays`）：任何陣列型別的宣告
- 禁用函式（`misc-forbid-functions`）：可配置禁用函式清單（如 `sort`、`printf`、`malloc`）
- 禁用 STL（`misc-forbid-stl`）：禁止使用 C++ 標準模板庫（std::vector、std::string、std::cout 等）
- 支援輸出 YAML 格式的診斷結果（可供 OJ 系統解析）
- 所有警告自動轉換為錯誤（`WarningsAsErrors: '*'`）

## 檔案一覽

- `CMakeLists.txt` — 建置設定（需要 LLVM/Clang 開發套件）
- `include/misc/*.h` — 各檢查的標頭檔
- `src/*.cpp` — 各檢查的實作與模組註冊
  - `ForbidLoopsCheck.cpp` — 禁用迴圈檢查
  - `ForbidArraysCheck.cpp` — 禁用陣列檢查
  - `ForbidFunctionsCheck.cpp` — 禁用特定函式檢查
  - `ForbidSTLCheck.cpp` — 禁用 STL 檢查（C++ 專用）
  - `RegisterModule.cpp` — 模組註冊入口
- `scripts/generate_tidy_config.py` — 生成 `.clang-tidy` 配置檔的腳本
  - 支援 `--forbid-loops`、`--forbid-arrays`、`--forbid-functions`、`--forbid-stl`
  - 支援 `--function-names` 指定禁用函式清單
  - 支援 `--output-dir` 指定輸出目錄
- `examples/` — 測試用範例程式
  - `main.c` — C 語言範例（包含陣列）
  - `main.cpp` — C++ 範例（包含迴圈與 std::sort）
- `presets/*.yaml` — 預設的 `.clang-tidy` 範例檔案

## 先決條件
- 已安裝 clang-tidy、Clang/LLVM 開發套件（headers & libs）以及 CMake。
- 推薦在 Linux 或 WSL（Windows Subsystem for Linux）下編譯/測試；在純 Windows/MSVC 下可能需調整 CMake toolchain、DLL 命名與 link 設定。

## 編譯（在 WSL / Linux / macOS）
在專案根目錄執行：

```bash
mkdir -p build
cd build
cmake ..
cmake --build . --config Release
```

成功後的輸出範例（Unix-like）會是：

- `build/libMiscTidyModule.so`

在 Windows（MSVC）環境下，產物可能為 `MiscTidyModule.dll` 或類似名稱，請依實際輸出路徑做調整。

> 如果你在 Windows 上不想處理 toolchain 的差異，建議安裝 WSL 並在 WSL 內部完成編譯與測試。

## 產生 .clang-tidy（題目自動化設定）
可以使用 `scripts/generate_tidy_config.py` 由題目設定自動建立 `.clang-tidy`：

### 基本用法

```bash
# 只禁用迴圈
python3 scripts/generate_tidy_config.py --forbid-loops

# 禁用迴圈和陣列
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays

# 禁用 STL（C++ 專用）
python3 scripts/generate_tidy_config.py --forbid-stl

# 禁用特定函式（需同時指定 --forbid-functions）
python3 scripts/generate_tidy_config.py --forbid-functions --function-names 'sort,printf,malloc'

# 組合使用：禁用迴圈、陣列和 STL
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays --forbid-stl

# 完整組合（加上禁用函式）
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays --forbid-stl --forbid-functions --function-names 'sort,printf'

# 指定輸出目錄（預設為當前目錄）
python3 scripts/generate_tidy_config.py --forbid-loops --output-dir examples
```

**生成範例：**

只禁用迴圈：
```yaml
Checks: misc-forbid-loops
WarningsAsErrors: '*'
```

禁用函式：
```yaml
CheckOptions:
- key: misc-forbid-functions.ForbiddenNames
  value: sort,printf,malloc
Checks: misc-forbid-functions
WarningsAsErrors: '*'
```

> **重要：**`WarningsAsErrors: '*'` 會將所有警告轉換為錯誤，確保違規代碼無法通過檢查。

這個步驟通常在 OJ 的題目設定階段由系統自動執行（出題者勾選要禁用的項目即可）。

## 執行 clang-tidy（範例）

### 推薦方式：使用 .clang-tidy 配置檔

先用腳本生成配置，clang-tidy 會自動讀取：

```bash
# 生成配置
python3 scripts/generate_tidy_config.py --forbid-arrays

# 執行檢查（不需指定 -checks）
clang-tidy main.c \
    -load ./build/libMiscTidyModule.so \
    -export-fixes=fixes.yaml \
    -- -std=c17
```

### 手動指定規則（不建議）

如果要針對單一檔案執行檢查並手動指定規則：

```bash
clang-tidy main.cpp \
    -load ./build/libMiscTidyModule.so \
    -checks='misc-forbid-loops,misc-forbid-arrays' \
    -- -std=c++17
```

### 輸出 YAML 格式的修復建議

使用 `-export-fixes` 可生成 YAML 格式的診斷結果，方便 OJ 後端解析：

```bash
clang-tidy main.c \
    -load ./build/libMiscTidyModule.so \
    -export-fixes=fixes.yaml \
    -- -std=c17
```

**注意：** 程式退出時可能出現 `free(): invalid pointer` 或 `pure virtual method called` 錯誤，這是 LLVM 14.0.0 動態模組的已知問題，**不影響檢查功能和 YAML 輸出**。fixes.yaml 會正常生成。

## 輸出格式：YAML 診斷結果

執行後 `-export-fixes=fixes.yaml` 會產生 YAML 格式的診斷結果：

```yaml
---
MainSourceFile: "/path/to/main.c"
Diagnostics:
  - DiagnosticName: misc-forbid-arrays
    DiagnosticMessage:
      Message: Array declaration is forbidden.
      FilePath: "/path/to/main.c"
      FileOffset: 137
      Replacements: []
    Level: Warning
    BuildDirectory: "/path/to/project"
```

OJ 系統可以解析 `Diagnostics` 陣列來決定要回傳給學生的錯誤訊息與位置。

> **注意：** 由於 `WarningsAsErrors: '*'` 的設定，所有 Warning 都會被視為 Error，確保違規代碼無法通過。

## 範例程式測試

專案包含 `examples/` 目錄，內有測試用程式碼：

- **`examples/main.c`** — 包含陣列宣告（觸發 `misc-forbid-arrays`）
- **`examples/main.cpp`** — 包含迴圈與 `std::sort` 呼叫（觸發 `misc-forbid-loops` 與 `misc-forbid-functions`）
- **`examples/.clang-tidy`** — 範例設定檔（啟用所有檢查並設定 `ForbiddenNames`）

### 測試 main.c（禁用陣列）

```bash
# 生成只禁用陣列的配置
python3 scripts/generate_tidy_config.py --forbid-arrays

# 執行檢查
clang-tidy examples/main.c \
  -load ./build/libMiscTidyModule.so \
  -export-fixes=main_c_result.yaml \
  -- -std=c17
```

**預期輸出：**

```text
examples/main.c:6:9: error: Array declaration is forbidden. [misc-forbid-arrays]
    int numbers[5] = {1, 2, 3, 4, 5};
        ^
```

### 測試 main.cpp（禁用迴圈與函式）

```bash
# 生成配置
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-functions --function-names 'sort'

# 執行檢查
clang-tidy examples/main.cpp \
  -load ./build/libMiscTidyModule.so \
  -export-fixes=main_cpp_result.yaml \
  -- -std=c++17
```

**預期輸出：**

```text
examples/main.cpp:10:10: error: Use of forbidden function 'sort' [misc-forbid-functions]
    std::sort(data.begin(), data.end());
         ^
examples/main.cpp:13:5: error: Loop statements (for/while/do) are forbidden. [misc-forbid-loops]
    for (int i = 0; i < data.size(); i++) {
    ^
```

### 使用 .clang-tidy 設定檔

可以在特定目錄生成配置檔，clang-tidy 會自動讀取：

```bash
# 為 examples 目錄生成配置
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays --forbid-functions --function-names 'sort,printf,malloc' --output-dir examples

# 在 examples 目錄下執行
cd examples
clang-tidy main.cpp -load ../build/libMiscTidyModule.so -export-fixes=result.yaml -- -std=c++17
```

生成的 `.clang-tidy` 範例：

```yaml
CheckOptions:
- key: misc-forbid-functions.ForbiddenNames
  value: sort,printf,malloc
Checks: misc-forbid-loops,misc-forbid-arrays,misc-forbid-functions
WarningsAsErrors: '*'
```

clang-tidy 會自動讀取該目錄的 `.clang-tidy` 設定並套用所有檢查規則。

## 自訂禁用函式清單

`misc-forbid-functions` 現在支援從 `.clang-tidy` 讀取選項：

```yaml
CheckOptions:
  - key: misc-forbid-functions.ForbiddenNames
    value: 'sort,printf,malloc,free,scanf'
```

多個函式名稱用逗號分隔（會自動處理前後空白）。

## 常見問題

**Q：為什麼程式退出時出現 `free(): invalid pointer` 或 `pure virtual method called` 錯誤？**  
A：這是 LLVM 14.0.0 動態載入模組的已知 bug，發生在程式退出卸載模組時。**這不影響檢查功能和輸出文件生成**，fixes.yaml 會正常產生，可以安全忽略這個錯誤。建議升級到 LLVM 15+ 以解決此問題，或在 OJ 系統中使用 `2>/dev/null || true` 抑制錯誤輸出。

**Q：如何在 OJ 系統中整合？**  
A：

1. 在題目設定介面讓出題者勾選要禁用的項目（迴圈/陣列/函式）
2. 系統呼叫 `generate_tidy_config.py` 產生 `.clang-tidy`
3. 在判題容器中執行 `clang-tidy` 並傳入 `-export-fixes=fixes.yaml`
4. 解析 YAML 的 `Diagnostics` 陣列，將錯誤訊息回傳給學生

範例整合腳本：

```bash
#!/bin/bash
# OJ 判題腳本範例
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays
clang-tidy student_code.c \
    -load ./build/libMiscTidyModule.so \
    -export-fixes=fixes.yaml \
    -- -std=c17 2>/dev/null || true

# 檢查是否有違規
if [ -f fixes.yaml ] && grep -q "DiagnosticName:" fixes.yaml; then
    echo "靜態檢查失敗：代碼違反題目限制"
    python3 parse_diagnostics.py fixes.yaml
    exit 1
fi
```

**Q：可以檢查 C 和 C++ 嗎？**  
A：可以。記得在編譯參數中指定正確的標準（`-std=c17` 或 `-std=c++17`）。注意 `misc-forbid-stl` 僅適用於 C++ 程式碼。

**Q：如何只禁用迴圈而不禁用函式？**  
A：使用 `--forbid-loops` 參數生成配置即可。只有在指定 `--forbid-functions` 時才會啟用函式檢查：

```bash
python3 scripts/generate_tidy_config.py --forbid-loops
```

**Q：STL 檢查會禁止哪些內容？**  
A：`misc-forbid-stl` 會禁止所有 `std::` 命名空間下的內容，包括：
- 容器：`std::vector`、`std::string`、`std::map`、`std::set` 等
- 算法：`std::sort`、`std::find`、`std::copy` 等
- I/O：`std::cout`、`std::cin`、`std::endl` 等
- 其他：`std::function`、`std::shared_ptr` 等所有 STL 組件
