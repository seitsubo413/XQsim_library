#!/usr/bin/env python3
"""
Publicフォルダ内の全量子回路をシミュレーション
"""
import urllib.request
import urllib.error
import json
import os
from datetime import datetime

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間

TEST_CIRCUITS = [
    # 2量子ビット回路
    {
        "name": "circuit_2q_bell_state",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    },
    {
        "name": "circuit_2q_cnot_simple",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    },
    {
        "name": "circuit_2q_h_both_cnot",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
h q[1];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    },
    {
        "name": "circuit_2q_x_cnot",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
x q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    },
    {
        "name": "circuit_2q_z_cnot",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
z q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    },
    # 3量子ビット回路
    {
        "name": "circuit_3q_bell_chain",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
h q[1];
cx q[1],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
"""
    },
    {
        "name": "circuit_3q_fan_out",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
"""
    },
    {
        "name": "circuit_3q_linear",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
"""
    },
    # 4量子ビット回路
    {
        "name": "circuit_4q_full_entangle",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
h q[1];
h q[2];
h q[3];
cx q[0],q[1];
cx q[0],q[2];
cx q[0],q[3];
cx q[1],q[2];
cx q[1],q[3];
cx q[2],q[3];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
"""
    },
    {
        "name": "circuit_4q_ghz",
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
measure q[3] -> c[3];
"""
    },
    {
        "name": "circuit_4q_ring",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
cx q[3],q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
"""
    },
    # 5量子ビット回路
    {
        "name": "circuit_5q_linear",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
cx q[3],q[4];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
"""
    },
    # 6量子ビット回路
    {
        "name": "circuit_6q_ladder",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
h q[0];
h q[1];
cx q[0],q[2];
cx q[1],q[3];
cx q[2],q[4];
cx q[3],q[5];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];
"""
    }
]

def run_trace(name: str, qasm: str) -> dict:
    """1つの回路をトレース"""
    print(f"\n{'='*60}")
    print(f"テスト: {name}")
    print(f"{'='*60}")
    
    payload = json.dumps({"qasm": qasm}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}/trace",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    start_time = datetime.now()
    
    try:
        print("シミュレーション実行中...")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            result = json.load(resp)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"✅ 完了 ({elapsed/60:.1f}分)")
        
        # clifford_t_execution_trace確認
        result_data = result.get("result", {})
        trace = result_data.get("clifford_t_execution_trace", {})
        
        if trace:
            summary = trace.get("summary", {})
            print(f"  総ゲート数: {summary.get('total_gates')}")
            print(f"  PPR: {summary.get('ppr_count')}, PPM: {summary.get('ppm_count')}, "
                  f"SQM: {summary.get('sqm_count')}, Pauli Frame: {summary.get('pauli_frame_count')}")
            print(f"  全ゲート追跡: {summary.get('all_gates_traced')}")
        else:
            print("  ⚠️ clifford_t_execution_trace が見つかりません")
        
        # 結果を保存
        output_dir = "test_results_all_public"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{name}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  結果を {output_file} に保存しました")
        
        return {"status": "success", "elapsed_minutes": elapsed/60}
        
    except urllib.error.HTTPError as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ HTTPエラー: {e.code} {e.reason} ({elapsed/60:.1f}分経過)")
        try:
            err_body = e.read().decode("utf-8")
            print(f"  詳細: {err_body[:200]}")
        except:
            pass
        return {"status": "error", "error": f"HTTP {e.code}", "elapsed_minutes": elapsed/60}
    except urllib.error.URLError as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ URLエラー: {e.reason} ({elapsed/60:.1f}分経過)")
        return {"status": "error", "error": str(e), "elapsed_minutes": elapsed/60}
    except KeyboardInterrupt:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n⚠️ 中断されました ({elapsed/60:.1f}分経過)")
        return {"status": "interrupted", "elapsed_minutes": elapsed/60}
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ エラー: {e} ({elapsed/60:.1f}分経過)")
        return {"status": "error", "error": str(e), "elapsed_minutes": elapsed/60}

def main():
    print("=" * 60)
    print("Publicフォルダ内の全量子回路をシミュレーション")
    print("=" * 60)
    print(f"総回路数: {len(TEST_CIRCUITS)}")
    
    results = []
    total_start = datetime.now()
    
    for i, test_case in enumerate(TEST_CIRCUITS, 1):
        print(f"\n[{i}/{len(TEST_CIRCUITS)}] {test_case['name']}")
        try:
            result = run_trace(test_case["name"], test_case["qasm"])
            results.append({
                "name": test_case["name"],
                "index": i,
                **result
            })
        except Exception as e:
            print(f"❌ {test_case['name']} で予期しないエラー: {e}")
            results.append({
                "name": test_case["name"],
                "index": i,
                "status": "error",
                "error": str(e)
            })
    
    total_elapsed = (datetime.now() - total_start).total_seconds()
    
    # サマリー
    print(f"\n{'='*60}")
    print("テストサマリー")
    print(f"{'='*60}")
    
    success_count = sum(1 for r in results if r.get("status") == "success")
    error_count = sum(1 for r in results if r.get("status") == "error")
    
    print(f"成功: {success_count}/{len(results)}")
    print(f"失敗: {error_count}/{len(results)}")
    print(f"総実行時間: {total_elapsed/60:.1f}分 ({total_elapsed/3600:.2f}時間)")
    
    print("\n詳細:")
    for r in results:
        status_icon = "✅" if r.get("status") == "success" else "❌"
        elapsed = r.get("elapsed_minutes", 0)
        print(f"  {status_icon} [{r.get('index', '?')}] {r['name']} ({elapsed:.1f}分)")
        if r.get("status") == "error":
            print(f"      エラー: {r.get('error', 'Unknown')}")
    
    # サマリーを保存
    summary_file = "test_results_all_public/summary.json"
    os.makedirs(os.path.dirname(summary_file), exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_circuits": len(TEST_CIRCUITS),
            "success_count": success_count,
            "error_count": error_count,
            "total_elapsed_minutes": total_elapsed/60,
            "results": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nサマリーを {summary_file} に保存しました")
    
    print(f"\n完了しました！")

if __name__ == "__main__":
    main()

