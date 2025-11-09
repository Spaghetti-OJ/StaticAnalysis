
本專案提供一組簡單的 clang-tidy 自訂規則（module），用於 Online Judge（OJ）在批改階段進行靜態分析，例如禁止迴圈、禁止陣列、或禁止特定函式的使用。

## 主要功能
- 禁用迴圈（`misc-forbid-loops`）：for / while / do-while。
- 禁用陣列（`misc-forbid-arrays`）：任何陣列型別的宣告。
- 禁用函式（`misc-forbid-functions`）：可在程式中擴充待禁用函式清單（範例預設包含 `sort`）。
- 支援輸出 clang-tidy fixes JSON（可供 OJ 系統解析）。

## 檔案一覽
- `CMakeLists.txt` — 建置設定（需要 LLVM/Clang 開發套件）。
- `include/misc/*.h`、`src/*.cpp` — 各檢查的標頭與實作。
- `presets/*.yaml` — 範例的 `.clang-tidy` preset 檔案（forbid_loops / forbid_arrays / forbid_both）。
- `scripts/generate_tidy_config.py` — 生成 `.clang-tidy` 的小腳本（可由題目設定自動呼叫）。
- `scripts/run_tidy.sh` — 在類 Unix 環境下的執行包裝腳本（示範如何一起載入模組並導出 JSON）。

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

```bash
python3 scripts/generate_tidy_config.py --forbid-loops --forbid-arrays
```

會產生像這樣的 `.clang-tidy`：

```yaml
Checks: 'misc-forbid-loops,misc-forbid-arrays'
WarningsAsErrors: '*'
```

這個步驟通常在 OJ 的題目設定階段由系統自動執行（出題者勾選要禁用的項目即可）。

## 執行 clang-tidy（範例）
如果要針對單一檔案執行檢查（Unix-like 範例）：

```bash
clang-tidy main.cpp \
	-load ./build/libMiscTidyModule.so \
	-checks='misc-forbid-loops,misc-forbid-arrays' \
	-- -std=c++17
```

若要輸出 JSON（使用 `-export-fixes`，方便 OJ 後端解析）：

```bash
clang-tidy main.c \
	-load ./build/libMiscTidyModule.so \
	-checks='misc-forbid-arrays' \
	-export-fixes=result.json \
	-- -std=c17
```

run_tidy.sh 是一個簡單的 wrapper（bash），可在類 Unix 環境下使用：

```bash
./scripts/run_tidy.sh main.cpp ./build/libMiscTidyModule.so 'misc-forbid-loops' -- -std=c++17
```

### Windows / PowerShell 注意事項
- 如果在 Windows 原生環境（PowerShell / MSVC）編譯，模組可能輸出為 `.dll`：請把 `-load` 的路徑改為對應的 DLL（例如 `-load .\build\MiscTidyModule.dll`），並確認 clang-tidy 可載入該 DLL（路徑、符號導出等）。
- `scripts/run_tidy.sh` 是 bash script；在 Windows 上可使用 WSL 或手動在 PowerShell 下撰寫等價指令：

PowerShell 範例：

```powershell
# 編譯（假設使用 CMake + MSVC toolchain）
mkdir build; cd build
cmake ..
cmake --build . --config Release

# 執行 clang-tidy（調整 -load 路徑為 dll）
clang-tidy ..\examples\main.cpp -load .\build\MiscTidyModule.dll -checks="misc-forbid-loops" -- -std=c++17
```

（注意：實際在 Windows 下可能需調整 CMakeLists 以正確 link 與匯出 DLL 符號，視 LLVM/Clang 的安裝方式而定。）

## 範例：檢查與 JSON 輸出
執行後 `-export-fixes=result.json` 會產生類似格式：

```json
{
	"MainSourceFile": "main.c",
	"Diagnostics": [
		{
			"DiagnosticName": "misc-forbid-arrays",
			"Message": "Array declaration is forbidden.",
			"FilePath": "main.c",
			"FileOffset": 32
		}
	]
}
```

OJ 系統可以解析 `Diagnostics` 陣列來決定要回傳給學生的錯誤訊息與位置。

## 範例程式測試

專案包含 `examples/` 目錄，內有測試用程式碼：

- **`examples/main.c`** — 包含陣列宣告（觸發 `misc-forbid-arrays`）
- **`examples/main.cpp`** — 包含迴圈與 `std::sort` 呼叫（觸發 `misc-forbid-loops` 與 `misc-forbid-functions`）
- **`examples/.clang-tidy`** — 範例設定檔（啟用所有檢查並設定 `ForbiddenNames`）

### 測試 main.c（禁用陣列）

```bash
clang-tidy examples/main.c \
  -load ./build/libMiscTidyModule.so \
  -checks='misc-forbid-arrays' \
  -export-fixes=main_c_result.json \
  -- -std=c17
```

**預期輸出：**
```
examples/main.c:6:9: error: Array declaration is forbidden. [misc-forbid-arrays]
    int numbers[5] = {1, 2, 3, 4, 5};
        ^
```

### 測試 main.cpp（禁用迴圈與函式）

```bash
clang-tidy examples/main.cpp \
  -load ./build/libMiscTidyModule.so \
  -checks='misc-forbid-loops,misc-forbid-functions' \
  -config="{CheckOptions: [{key: misc-forbid-functions.ForbiddenNames, value: 'sort'}]}" \
  -export-fixes=main_cpp_result.json \
  -- -std=c++17
```

**預期輸出：**
```
examples/main.cpp:10:10: error: Use of forbidden function 'sort' [misc-forbid-functions]
    std::sort(data.begin(), data.end());
         ^
examples/main.cpp:13:5: error: Loop statements (for/while/do) are forbidden. [misc-forbid-loops]
    for (int i = 0; i < data.size(); i++) {
    ^
```

### 使用 .clang-tidy 設定檔

`examples/.clang-tidy` 已經設定好所有檢查與選項：

```yaml
Checks: 'misc-forbid-loops,misc-forbid-arrays,misc-forbid-functions'
WarningsAsErrors: '*'
CheckOptions:
  - key: misc-forbid-functions.ForbiddenNames
    value: 'sort,printf,malloc'
```

在 `examples/` 目錄下執行：

```bash
cd examples
clang-tidy main.cpp -load ../build/libMiscTidyModule.so -export-fixes=result.json -- -std=c++17
```

clang-tidy 會自動讀取 `.clang-tidy` 設定並套用所有檢查規則。

### 一鍵測試腳本

也可使用 `scripts/test_examples.sh`（bash）：

```bash
chmod +x scripts/test_examples.sh
./scripts/test_examples.sh
```

腳本會依序測試 `main.c` 與 `main.cpp` 並產生 JSON 輸出。

## 自訂禁用函式清單

`misc-forbid-functions` 現在支援從 `.clang-tidy` 讀取選項：

```yaml
CheckOptions:
  - key: misc-forbid-functions.ForbiddenNames
    value: 'sort,printf,malloc,free,scanf'
```

多個函式名稱用逗號分隔（會自動處理前後空白）。

## 常見問題

**Q：為什麼在 Windows 下無法載入 `.dll`？**  
A：可能是 CMake 沒有正確匯出符號、或 clang-tidy 期待不同的 ABI/CRT。常見做法是使用 WSL 或 Linux 容器來避免這些差異。

**Q：如何在 OJ 系統中整合？**  
A：
1. 在題目設定介面讓出題者勾選要禁用的項目（迴圈/陣列/函式）
2. 系統呼叫 `generate_tidy_config.py` 產生 `.clang-tidy`
3. 在判題容器中執行 `clang-tidy` 並傳入 `-export-fixes=result.json`
4. 解析 JSON 的 `Diagnostics` 陣列，將錯誤訊息回傳給學生

**Q：可以檢查 C 和 C++ 嗎？**  
A：可以。記得在編譯參數中指定正確的標準（`-std=c17` 或 `-std=c++17`）。
