#!/usr/bin/env python3
"""XQsim API テストスクリプト v3 - 複雑な回路"""

import requests
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = "/app/test_results_v3"

# 複雑なテストケース
TEST_CASES = [
    {
        "name": "test_qft_3qubit",
        "description": "3量子ビット量子フーリエ変換 (QFT)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// QFT on 3 qubits
h q[0];
cu1(pi/2) q[1],q[0];
cu1(pi/4) q[2],q[0];
h q[1];
cu1(pi/2) q[2],q[1];
h q[2];
// Swap q[0] and q[2] via CNOTs
cx q[0],q[2];
cx q[2],q[0];
cx q[0],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
    {
        "name": "test_grover_2qubit",
        "description": "2量子ビットGroverアルゴリズム (1回反復)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[2];
// Initialize superposition
h q[0];
h q[1];
x q[2];
h q[2];
// Oracle for |11>
ccx q[0],q[1],q[2];
// Diffusion operator
h q[0];
h q[1];
x q[0];
x q[1];
h q[1];
cx q[0],q[1];
h q[1];
x q[0];
x q[1];
h q[0];
h q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    },
    {
        "name": "test_entangle_chain_4q",
        "description": "4量子ビット連鎖エンタングルメント",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];"""
    },
    {
        "name": "test_ghz_4qubit",
        "description": "4量子ビットGHZ状態",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
cx q[0],q[3];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];"""
    },
    {
        "name": "test_teleportation",
        "description": "量子テレポーテーション回路",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// Prepare state to teleport (|+> state)
h q[0];
// Create Bell pair between q[1] and q[2]
h q[1];
cx q[1],q[2];
// Bell measurement
cx q[0],q[1];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];
// Conditional operations (classically controlled)
// In QASM we use c-gates
cx q[1],q[2];
cz q[0],q[2];
measure q[2] -> c[2];"""
    },
    {
        "name": "test_bernstein_vazirani_4bit",
        "description": "Bernstein-Vazirani (秘密文字列 s=1011)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[4];
// Initialize
x q[4];
h q[0];
h q[1];
h q[2];
h q[3];
h q[4];
// Oracle for s=1011 (CNOT on positions 0,1,3)
cx q[0],q[4];
cx q[1],q[4];
cx q[3],q[4];
// Final Hadamard
h q[0];
h q[1];
h q[2];
h q[3];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];"""
    },
    {
        "name": "test_vqe_ansatz_2layer",
        "description": "VQE Ansatz (2層、固定パラメータ)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
// Layer 1: Ry rotations (using H+Rz+H approximation)
h q[0];
h q[1];
h q[2];
h q[3];
// Entangling layer 1
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
// Layer 2: Ry rotations
h q[0];
h q[1];
h q[2];
h q[3];
// Entangling layer 2
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
// Final measurement
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];"""
    },
    {
        "name": "test_qaoa_maxcut_simple",
        "description": "QAOA MaxCut (3頂点グラフ、1層)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// Initial superposition
h q[0];
h q[1];
h q[2];
// Cost layer (ZZ interactions via CNOT-Rz-CNOT)
cx q[0],q[1];
rz(0.5) q[1];
cx q[0],q[1];
cx q[1],q[2];
rz(0.5) q[2];
cx q[1],q[2];
cx q[0],q[2];
rz(0.5) q[2];
cx q[0],q[2];
// Mixer layer (Rx via H-Rz-H)
h q[0];
rz(0.7) q[0];
h q[0];
h q[1];
rz(0.7) q[1];
h q[1];
h q[2];
rz(0.7) q[2];
h q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];"""
    },
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 70)
    print("XQsim API テスト v3 - 複雑な量子回路")
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
            print("実行中... (複雑な回路のため時間がかかります)")
            
            resp = requests.post(
                f"{BASE_URL}/trace",
                json=body,
                timeout=7200  # 2時間タイムアウト
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if resp.status_code == 200:
                result = resp.json()
                
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
                try:
                    error_detail = resp.json().get("detail", resp.text)
                except:
                    error_detail = resp.text
                
                summary_entry = {
                    "name": test["name"],
                    "description": test["description"],
                    "status": "FAILED",
                    "http_status": resp.status_code,
                    "error": error_detail[:300],
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
    
    # サマリー
    print("=" * 70)
    print("テスト完了 - サマリー")
    print("=" * 70)
    
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    summary_output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "test_type": "Complex quantum circuits",
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
            print(f"   サイクル: {cycles:,}, QISA命令: {item.get('num_qisa_instructions', 0)}, イベント: {item['num_events']}")
        else:
            print(f"   エラー: {item.get('error', 'unknown')[:60]}...")
        print()
    
    print(f"成功: {summary_output['passed']}/{summary_output['total_tests']}")
    print(f"サマリー保存先: {summary_file}")


if __name__ == "__main__":
    main()

