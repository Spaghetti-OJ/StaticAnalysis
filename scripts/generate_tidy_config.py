#!/usr/bin/env python3
import sys
import yaml
import os

# 解析命令列參數
options = {
    "loops": "--forbid-loops" in sys.argv,
    "arrays": "--forbid-arrays" in sys.argv,
    "functions": "--forbid-functions" in sys.argv,
}

# 擷取禁止函式清單，例如：
#   python3 generate_tidy_config.py --forbid-functions --function-names printf,scanf,malloc
forbidden_funcs = []
if "--function-names" in sys.argv:
    idx = sys.argv.index("--function-names")
    if idx + 1 < len(sys.argv):
        # 支援逗號分隔的函式清單
        forbidden_funcs = sys.argv[idx + 1].split(",")

# 輸出目錄（預設為當前目錄）
output_dir = "."
if "--output-dir" in sys.argv:
    idx = sys.argv.index("--output-dir")
    if idx + 1 < len(sys.argv):
        output_dir = sys.argv[idx + 1]
os.makedirs(output_dir, exist_ok=True)

# 檢查要啟用的自訂規則
checks = []
if options["loops"]:
    checks.append("misc-forbid-loops")
if options["arrays"]:
    checks.append("misc-forbid-arrays")
if options["functions"]:
    checks.append("misc-forbid-functions")

# clang-tidy 設定
config = {
    "Checks": ",".join(checks) if checks else "-*",
    "WarningsAsErrors": "*",
}

# 若有禁止函式清單則加入自訂參數
if forbidden_funcs and options["functions"]:
    config["CheckOptions"] = [{
        "key": "misc-forbid-functions.ForbiddenNames",
        "value": ",".join(forbidden_funcs)
    }]

# 若沒有啟用 --forbid-functions，則忽略 --function-names 並提示
if forbidden_funcs and not options["functions"]:
    print("[note] --function-names provided without --forbid-functions; names will be ignored.")

# 寫入設定檔
output_path = os.path.join(output_dir, ".clang-tidy")
with open(output_path, "w") as f:
    yaml.dump(config, f)

# 顯示結果
print("✅ Generated .clang-tidy at:", output_path)
print("✅ Checks:", checks or ["none"])
if forbidden_funcs:
    print("🚫 Forbidden functions:", ", ".join(forbidden_funcs))
