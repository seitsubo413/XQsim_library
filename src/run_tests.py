#!/usr/bin/env python3
"""XQsim API テストスクリプト"""

import requests
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = "/app/test_results"

# テストケース定義
TEST_CASES = [
    {
        "name": "test1_single_h",
        "description": "1量子ビット: Hゲートのみ",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];"""
    },
    {
        "name": "test2_bell_state",
        "description": "2量子ビット: Bell状態 (H + CNOT)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test3_ghz_3qubit",
        "description": "3量子ビット: GHZ状態",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
    {
        "name": "test4_multiple_h",
        "description": "3量子ビット: 複数のHゲート",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
h q[1];
h q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
    {
        "name": "test5_x_gate",
        "description": "2量子ビット: Xゲート (NOT)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
x q[0];
x q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test6_z_gate",
        "description": "2量子ビット: Zゲート",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
z q[0];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    }
]


def main():
    # 出力ディレクトリ作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 50)
    print("XQsim API テスト開始")
    print("=" * 50)
    print()
    
    # ヘルスチェック
    print("API ヘルスチェック中...")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        health = resp.json()
        print(f"API Status: {health.get('status', 'unknown')}")
        print()
    except Exception as e:
        print(f"エラー: APIに接続できません: {e}")
        return
    
    summary = []
    
    # 各テストケースを実行
    for i, test in enumerate(TEST_CASES):
        print("-" * 50)
        print(f"テスト {i+1}/{len(TEST_CASES)}: {test['name']}")
        print(f"説明: {test['description']}")
        print()
        
        body = {
            "qasm": test["qasm"],
            "config": "example_cmos_d5"
        }
        
        start_time = time.time()
        
        try:
            print("実行中... (時間がかかる場合があります)")
            
            resp = requests.post(
                f"{BASE_URL}/trace",
                json=body,
                timeout=3600  # 1時間タイムアウト
            )
            resp.raise_for_status()
            result = resp.json()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 結果をファイルに保存
            output_file = os.path.join(OUTPUT_DIR, f"{test['name']}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # サマリー情報を収集
            meta = result.get("result", {}).get("meta", {})
            events = result.get("result", {}).get("patch", {}).get("events", [])
            
            summary_entry = {
                "name": test["name"],
                "description": test["description"],
                "status": "SUCCESS",
                "total_cycles": meta.get("total_cycles"),
                "elapsed_seconds": meta.get("elapsed_seconds"),
                "num_patches": meta.get("num_patches"),
                "num_events": len(events),
                "termination_reason": meta.get("termination_reason"),
                "local_duration": round(duration, 2)
            }
            summary.append(summary_entry)
            
            print("完了!")
            print(f"  サイクル数: {meta.get('total_cycles')}")
            print(f"  実行時間: {meta.get('elapsed_seconds')} 秒")
            print(f"  パッチ数: {meta.get('num_patches')}")
            print(f"  イベント数: {len(events)}")
            print(f"  保存先: {output_file}")
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            summary_entry = {
                "name": test["name"],
                "description": test["description"],
                "status": "FAILED",
                "error": str(e),
                "local_duration": round(duration, 2)
            }
            summary.append(summary_entry)
            
            print(f"失敗: {e}")
        
        print()
    
    # サマリーを保存
    print("=" * 50)
    print("テスト完了 - サマリー")
    print("=" * 50)
    
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    summary_output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": len(TEST_CASES),
        "passed": len([s for s in summary if s["status"] == "SUCCESS"]),
        "failed": len([s for s in summary if s["status"] == "FAILED"]),
        "results": summary
    }
    
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2, ensure_ascii=False)
    
    print()
    print("結果サマリー:")
    for item in summary:
        status = item["status"]
        if status == "SUCCESS":
            print(f"  [SUCCESS] {item['name']}: {item['description']}")
            print(f"            サイクル: {item['total_cycles']}, イベント: {item['num_events']}")
        else:
            print(f"  [FAILED] {item['name']}: {item['description']}")
            print(f"           エラー: {item.get('error', 'unknown')}")
    
    print()
    print(f"サマリー保存先: {summary_file}")
    print()
    print("個別の結果ファイル:")
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".json"):
            print(f"  - {f}")


if __name__ == "__main__":
    main()

