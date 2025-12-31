#!/usr/bin/env python3
"""XQsim API テストスクリプト v2 - CNOT含む回路のみ"""

import requests
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = "/app/test_results_v2"

# テストケース定義（全てCNOTを含む）
TEST_CASES = [
    {
        "name": "test_cnot_simple",
        "description": "2量子ビット: シンプルなCNOT",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test_h_cnot_2q",
        "description": "2量子ビット: H + CNOT (Bell状態)",
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
        "name": "test_x_cnot_2q",
        "description": "2量子ビット: X + CNOT",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
x q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test_z_cnot_2q",
        "description": "2量子ビット: Z + CNOT",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
z q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test_h_both_cnot",
        "description": "2量子ビット: 両方にH + CNOT",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
h q[1];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test_swap_via_cnot",
        "description": "2量子ビット: SWAP（3つのCNOT）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
cx q[1],q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test_3q_linear",
        "description": "3量子ビット: 線形CNOT (0→1→2)",
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
        "name": "test_3q_fan_out",
        "description": "3量子ビット: ファンアウト (0→1, 0→2)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
]


def main():
    # 出力ディレクトリ作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("XQsim API テスト v2 - CNOT含む回路")
    print("=" * 60)
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
        print("-" * 60)
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
                timeout=3600
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if resp.status_code == 200:
                result = resp.json()
                
                # 結果をファイルに保存
                output_file = os.path.join(OUTPUT_DIR, f"{test['name']}.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
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
                
                print("✅ 成功!")
                print(f"  サイクル数: {meta.get('total_cycles')}")
                print(f"  実行時間: {meta.get('elapsed_seconds')} 秒")
                print(f"  イベント数: {len(events)}")
                
            else:
                # エラーレスポンスの詳細を取得
                try:
                    error_detail = resp.json().get("detail", resp.text)
                except:
                    error_detail = resp.text
                
                summary_entry = {
                    "name": test["name"],
                    "description": test["description"],
                    "status": "FAILED",
                    "http_status": resp.status_code,
                    "error": error_detail[:200],  # 最初の200文字
                    "local_duration": round(duration, 2)
                }
                summary.append(summary_entry)
                
                print(f"❌ 失敗 (HTTP {resp.status_code})")
                print(f"  エラー: {error_detail[:100]}...")
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            summary_entry = {
                "name": test["name"],
                "description": test["description"],
                "status": "ERROR",
                "error": str(e),
                "local_duration": round(duration, 2)
            }
            summary.append(summary_entry)
            
            print(f"❌ エラー: {e}")
        
        print()
    
    # サマリーを保存
    print("=" * 60)
    print("テスト完了 - サマリー")
    print("=" * 60)
    
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    summary_output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hypothesis": "CNOTを含む回路のみが成功する",
        "total_tests": len(TEST_CASES),
        "passed": len([s for s in summary if s["status"] == "SUCCESS"]),
        "failed": len([s for s in summary if s["status"] in ["FAILED", "ERROR"]]),
        "results": summary
    }
    
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2, ensure_ascii=False)
    
    print()
    print("結果サマリー:")
    print("-" * 60)
    for item in summary:
        status_icon = "✅" if item["status"] == "SUCCESS" else "❌"
        print(f"{status_icon} {item['name']}: {item['description']}")
        if item["status"] == "SUCCESS":
            print(f"   サイクル: {item['total_cycles']}, イベント: {item['num_events']}")
        else:
            print(f"   エラー: {item.get('error', 'unknown')[:50]}...")
    
    print()
    print(f"成功: {summary_output['passed']}/{summary_output['total_tests']}")
    print(f"サマリー保存先: {summary_file}")


if __name__ == "__main__":
    main()

