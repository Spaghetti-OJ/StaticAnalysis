#!/usr/bin/env python3
"""
API 測試腳本
示範如何使用 Clang-Tidy API
"""

import requests
import json

BASE_URL = "http://localhost:5000"
TOKEN = "test_token_123"  # 測試用 token

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_1_create_submission():
    """測試建立提交"""
    print("\n1️⃣  建立測試提交...")
    
    code = """
#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    std::vector<int> data = {5, 2, 8, 1, 9};
    std::sort(data.begin(), data.end());
    
    for (int i = 0; i < data.size(); i++) {
        std::cout << data[i] << " ";
    }
    
    return 0;
}
"""
    
    response = requests.post(
        f"{BASE_URL}/submission",
        json={
            "problem_id": 1,
            "code": code,
            "language": "cpp"
        }
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return result.get("submission_id")


def test_2_save_requirements(problem_id=1):
    """測試儲存規則需求"""
    print(f"\n2️⃣  儲存題目 {problem_id} 的規則需求...")
    
    response = requests.post(
        f"{BASE_URL}/lint/requirements",
        headers=headers,
        json={
            "problem_id": problem_id,
            "rules": [
                "--forbid-loops",
                "--forbid-stl",
                "--forbid-functions=printf,malloc"
            ]
        }
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return result


def test_3_generate_config(problem_id=1):
    """測試生成 .clang-tidy"""
    print(f"\n3️⃣  生成題目 {problem_id} 的 .clang-tidy 配置...")
    
    response = requests.post(
        f"{BASE_URL}/lint/generate",
        headers=headers,
        json={
            "problem_id": problem_id,
            "rules": [
                "--forbid-loops",
                "--forbid-stl"
            ],
            "language_type": 1
        }
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        print(f"\n生成的配置內容：")
        print(result.get("config_content"))
    
    return result


def test_4_run_lint(submission_id, problem_id=1):
    """測試執行靜態分析"""
    print(f"\n4️⃣  對提交 {submission_id} 執行靜態分析...")
    
    response = requests.post(
        f"{BASE_URL}/lint/run",
        json={
            "submission_id": submission_id,
            "problem_id": problem_id,
            "language_type": 1,
            "timeout_sec": 30,
            "export_fixes": True
        }
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return result.get("run_id")


def test_5_save_report(submission_id, problem_id=1, run_id="run_test"):
    """測試儲存分析報告"""
    print(f"\n5️⃣  儲存分析報告...")
    
    response = requests.post(
        f"{BASE_URL}/lint/report",
        headers=headers,
        json={
            "submission_id": submission_id,
            "problem_id": problem_id,
            "run_id": run_id,
            "result": {
                "passed": False,
                "violations": [
                    {
                        "rule": "misc-forbid-loops",
                        "message": "Loop statements are forbidden.",
                        "file": "code.cpp",
                        "line": 10,
                        "column": 5
                    },
                    {
                        "rule": "misc-forbid-stl",
                        "message": "Use of STL is forbidden.",
                        "file": "code.cpp",
                        "line": 7,
                        "column": 5
                    }
                ],
                "total_violations": 2,
                "execution_time_ms": 245
            }
        }
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return result


def test_6_get_submission(submission_id):
    """測試查詢提交"""
    print(f"\n6️⃣  查詢提交 {submission_id}...")
    
    response = requests.get(
        f"{BASE_URL}/submission/{submission_id}",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result


def test_health():
    """測試健康檢查"""
    print("\n🏥 健康檢查...")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return result


def run_full_test():
    """執行完整測試流程"""
    print("=" * 60)
    print("🧪 Clang-Tidy API 完整測試")
    print("=" * 60)
    
    try:
        # 健康檢查
        test_health()
        
        # 1. 建立提交
        submission_id = test_1_create_submission()
        if not submission_id:
            print("❌ 建立提交失敗")
            return
        
        # 2. 儲存規則需求
        test_2_save_requirements(problem_id=1)
        
        # 3. 生成配置
        test_3_generate_config(problem_id=1)
        
        # 4. 執行分析
        run_id = test_4_run_lint(submission_id, problem_id=1)
        
        # 5. 儲存報告
        if run_id:
            test_5_save_report(submission_id, problem_id=1, run_id=run_id)
        
        # 6. 查詢提交
        test_6_get_submission(submission_id)
        
        print("\n" + "=" * 60)
        print("✅ 測試完成！")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 無法連接到 API 伺服器")
        print("請先執行: uvicorn api.app:app --host 0.0.0.0 --port 5000")
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")


if __name__ == "__main__":
    run_full_test()
