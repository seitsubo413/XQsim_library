#!/usr/bin/env python3
"""
2つの回路でclifford_t_execution_traceをテスト
"""
import urllib.request
import urllib.error
import json
import os
from datetime import datetime

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間

TEST_CIRCUITS = [
    {
        "name": "test_4q_linear",
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
        "name": "test_10q_complex",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];

// フェーズ1: 全量子ビットをHで初期化
h q[0];
h q[1];
h q[2];
h q[3];
h q[4];
h q[5];
h q[6];
h q[7];
h q[8];
h q[9];

// フェーズ2: グループ1 (0-3)
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
cx q[0],q[2];
cx q[1],q[3];

// フェーズ3: グループ2 (4-6)
cx q[4],q[5];
cx q[5],q[6];
cx q[4],q[6];

// フェーズ4: グループ3 (7-9)
cx q[7],q[8];
cx q[8],q[9];
cx q[7],q[9];

// フェーズ5: グループ間クロスエンタングルメント
cx q[0],q[4];
cx q[1],q[5];
cx q[2],q[6];
cx q[3],q[7];
cx q[4],q[8];
cx q[5],q[9];
cx q[0],q[7];
cx q[1],q[8];
cx q[2],q[9];

// フェーズ6: 追加の複雑なCNOT
cx q[0],q[5];
cx q[1],q[6];
cx q[2],q[7];
cx q[3],q[8];
cx q[4],q[9];
cx q[5],q[0];
cx q[6],q[1];
cx q[7],q[2];
cx q[8],q[3];
cx q[9],q[4];

// フェーズ7: 単一量子ビットゲート
h q[0];
h q[2];
h q[4];
h q[6];
h q[8];
x q[1];
x q[3];
x q[5];
x q[7];
x q[9];
z q[0];
z q[2];
z q[4];
z q[6];
z q[8];

// フェーズ8: さらに複雑なエンタングルメント
cx q[0],q[9];
cx q[1],q[8];
cx q[2],q[7];
cx q[3],q[6];
cx q[4],q[5];
cx q[9],q[0];
cx q[8],q[1];
cx q[7],q[2];
cx q[6],q[3];
cx q[5],q[4];

// フェーズ9: リング構造（部分）
cx q[0],q[1];
cx q[2],q[3];
cx q[4],q[5];
cx q[6],q[7];
cx q[8],q[9];

// フェーズ10: 最終的なHゲート
h q[0];
h q[1];
h q[2];
h q[3];
h q[4];
h q[5];
h q[6];
h q[7];
h q[8];
h q[9];

measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];
measure q[6] -> c[6];
measure q[7] -> c[7];
measure q[8] -> c[8];
measure q[9] -> c[9];
"""
    }
]

def run_trace(name: str, qasm: str) -> dict:
    """1つの回路をトレース"""
    print(f"\n{'='*60}")
    print(f"テスト: {name}")
    print(f"{'='*60}")
    print(f"回路: {len(qasm.split(chr(10)))}行")
    
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
            print(f"  PPR数: {summary.get('ppr_count')}")
            print(f"  PPM数: {summary.get('ppm_count')}")
            print(f"  SQM数: {summary.get('sqm_count')}")
            print(f"  Pauli Frame数: {summary.get('pauli_frame_count')}")
            print(f"  全ゲート追跡: {summary.get('all_gates_traced')}")
            
            # 最初の3ゲートと最後の3ゲートを表示
            gates = trace.get("gates", [])
            print(f"\n  ゲート例 (最初の3つ):")
            for i, gate in enumerate(gates[:3]):
                gate_name = gate.get("gate")
                qubits = gate.get("qubits")
                exec_type = gate.get("execution_type")
                print(f"    [{gate.get('gate_idx')}] {gate_name} q{qubits} -> {exec_type}")
            
            if len(gates) > 6:
                print(f"  ... ({len(gates) - 6}ゲート省略) ...")
                print(f"  ゲート例 (最後の3つ):")
                for gate in gates[-3:]:
                    gate_name = gate.get("gate")
                    qubits = gate.get("qubits")
                    exec_type = gate.get("execution_type")
                    print(f"    [{gate.get('gate_idx')}] {gate_name} q{qubits} -> {exec_type}")
        else:
            print("  ⚠️ clifford_t_execution_trace が見つかりません")
        
        # 結果を保存
        output_dir = "test_results_two_circuits"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{name}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n  結果を {output_file} に保存しました")
        
        return {"status": "success", "result": result}
        
    except urllib.error.HTTPError as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ HTTPエラー: {e.code} {e.reason} ({elapsed/60:.1f}分経過)")
        try:
            err_body = e.read().decode("utf-8")
            print(f"  詳細: {err_body[:200]}")
        except:
            pass
        return {"status": "error", "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ URLエラー: {e.reason} ({elapsed/60:.1f}分経過)")
        return {"status": "error", "error": str(e)}
    except KeyboardInterrupt:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n⚠️ 中断されました ({elapsed/60:.1f}分経過)")
        return {"status": "interrupted"}
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ エラー: {e} ({elapsed/60:.1f}分経過)")
        return {"status": "error", "error": str(e)}

def main():
    print("=" * 60)
    print("2つの回路でclifford_t_execution_traceをテスト")
    print("=" * 60)
    
    results = []
    
    for test_case in TEST_CIRCUITS:
        try:
            result = run_trace(test_case["name"], test_case["qasm"])
            results.append({
                "name": test_case["name"],
                **result
            })
        except Exception as e:
            print(f"❌ {test_case['name']} で予期しないエラー: {e}")
            results.append({
                "name": test_case["name"],
                "status": "error",
                "error": str(e)
            })
    
    # サマリー
    print(f"\n{'='*60}")
    print("テストサマリー")
    print(f"{'='*60}")
    for r in results:
        status = "✅ SUCCESS" if r.get("status") == "success" else f"❌ {r.get('status', 'UNKNOWN')}"
        print(f"  {r['name']}: {status}")
    
    print(f"\n完了しました！")

if __name__ == "__main__":
    main()

