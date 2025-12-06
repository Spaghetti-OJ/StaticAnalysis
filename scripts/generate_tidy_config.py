#!/usr/bin/env python3
import sys
import yaml
import os

# 解析命令列參數
options = {
    "loops": "--forbid-loops" in sys.argv,
    "arrays": "--forbid-arrays" in sys.argv,
    "functions": "--forbid-functions" in sys.argv,
    "stl": "--forbid-stl" in sys.argv,
    "id_naming": "--identifier-naming" in sys.argv,
    "include_cleaner": "--include-cleaner" in sys.argv,
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
if options["stl"]:
    checks.append("misc-forbid-stl")
if options["id_naming"]:
    checks.append("readability-identifier-naming")
if options["include_cleaner"]:
    checks.append("misc-include-cleaner")

# 解析命名規則
allowed_cases = {
    "camelBack",
    "CamelCase",
    "snake_case",
    "UPPER_CASE",
    "lower_case",
}
case_flags = {
    "--fn-case": "FunctionCase",
    "--var-case": "VariableCase",
    "--class-case": "ClassCase",
    "--param-case": "ParameterCase",
    "--enum-case": "EnumConstantCase",
}
naming_options = {}
for flag, key in case_flags.items():
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            val = sys.argv[idx + 1]
            if val not in allowed_cases:
                print(f"[warn] {flag} unsupported case: {val} (allowed: {', '.join(sorted(allowed_cases))})")
            else:
                naming_options[key] = val

# clang-tidy 設定
config = {
    "Checks": ",".join(checks) if checks else "-*",
    # 只將自訂 misc 規則視為錯誤，新加入的內建規則維持警告級別
    "WarningsAsErrors": "misc-forbid-*",
}

# 若有禁止函式清單則加入自訂參數
check_options = []

if forbidden_funcs and options["functions"]:
    check_options.append({
        "key": "misc-forbid-functions.ForbiddenNames",
        "value": ",".join(forbidden_funcs)
    })

if options["id_naming"]:
    for k, v in naming_options.items():
        check_options.append({
            "key": f"readability-identifier-naming.{k}",
            "value": v
        })

if check_options:
    config["CheckOptions"] = check_options

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
