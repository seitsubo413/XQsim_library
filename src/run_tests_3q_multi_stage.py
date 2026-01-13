#!/usr/bin/env python3
"""XQsim API テストスクリプト - 3量子ビット多段回路"""

import requests
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = "/app/test_results_3q_multi_stage"

# 3量子ビット多段回路のテストケース
TEST_CASES = [
    {
        "name": "test_3q_linear_chain_4stage",
        "description": "3量子ビット: 線形連鎖（4段CNOT）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[0],q[1];
cx q[1],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
    {
        "name": "test_3q_fan_out_chain",
        "description": "3量子ビット: ファンアウト連鎖（5段）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
    {
        "name": "test_3q_mixed_operations",
        "description": "3量子ビット: 混合操作（H/X/Z+CNOT、6段）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
x q[1];
cx q[0],q[1];
z q[0];
h q[2];
cx q[1],q[2];
x q[0];
cx q[0],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
    {
        "name": "test_3q_ghz_chain",
        "description": "3量子ビット: GHZ状態連鎖（3回生成）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// GHZ 1
h q[0];
cx q[0],q[1];
cx q[0],q[2];
// GHZ 2
h q[0];
cx q[0],q[1];
cx q[0],q[2];
// GHZ 3
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
    {
        "name": "test_3q_deep_circuit",
        "description": "3量子ビット: 深い回路（8段CNOT連鎖）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
x q[1];
cx q[1],q[2];
h q[2];
cx q[0],q[2];
z q[0];
cx q[0],q[1];
h q[1];
cx q[1],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
]


def main():
    # 出力ディレクトリ作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 70)
    print("XQsim API テスト - 3量子ビット多段回路")
    print("=" * 70)
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
        print("-" * 70)
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
                timeout=None  # タイムアウトなし
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
                qisa = result.get("result", {}).get("compiled", {}).get("qisa", [])
                
                summary_entry = {
                    "name": test["name"],
                    "description": test["description"],
                    "status": "SUCCESS",
                    "total_cycles": meta.get("total_cycles"),
                    "elapsed_seconds": meta.get("elapsed_seconds"),
                    "num_patches": meta.get("num_patches"),
                    "num_events": len(events),
                    "num_qisa_instructions": len(qisa),
                    "termination_reason": meta.get("termination_reason"),
                    "local_duration": round(duration, 2)
                }
                summary.append(summary_entry)
                
                print("✅ 成功!")
                print(f"  サイクル数: {meta.get('total_cycles'):,}")
                print(f"  実行時間: {meta.get('elapsed_seconds'):.1f} 秒")
                print(f"  QISA命令数: {len(qisa)}")
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
                    "error": error_detail[:300],  # 最初の300文字
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
    print("=" * 70)
    print("テスト完了 - サマリー")
    print("=" * 70)
    
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    summary_output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "test_type": "3量子ビット多段回路",
        "total_tests": len(TEST_CASES),
        "passed": len([s for s in summary if s["status"] == "SUCCESS"]),
        "failed": len([s for s in summary if s["status"] in ["FAILED", "ERROR"]]),
        "results": summary
    }
    
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2, ensure_ascii=False)
    
    print()
    print("結果サマリー:")
    print("-" * 70)
    for item in summary:
        status_icon = "✅" if item["status"] == "SUCCESS" else "❌"
        print(f"{status_icon} {item['name']}")
        print(f"   {item['description']}")
        if item["status"] == "SUCCESS":
            cycles = item.get('total_cycles', 0)
            qisa_count = item.get('num_qisa_instructions', 0)
            events_count = item.get('num_events', 0)
            print(f"   サイクル: {cycles:,}, QISA命令: {qisa_count}, イベント: {events_count}")
        else:
            print(f"   エラー: {item.get('error', 'unknown')[:60]}...")
        print()
    
    print(f"成功: {summary_output['passed']}/{summary_output['total_tests']}")
    print(f"サマリー保存先: {summary_file}")


if __name__ == "__main__":
    main()

