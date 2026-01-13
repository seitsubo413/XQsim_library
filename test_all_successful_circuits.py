#!/usr/bin/env python3
"""
全成功回路の再シミュレーション
- logical_qubit_mapping 情報を含む新バージョン
- これまで成功したすべての回路を再実行
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
import os

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間（無制限）

# これまで成功したすべての回路
ALL_SUCCESSFUL_CIRCUITS = [
    # ===== 2量子ビット回路 =====
    {
        "name": "circuit_2q_cnot_simple",
        "description": "2量子ビット: シンプルなCNOT",
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
        "name": "circuit_2q_bell_state",
        "description": "2量子ビット: Bell状態 (H + CNOT)",
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
        "name": "circuit_2q_x_cnot",
        "description": "2量子ビット: X + CNOT",
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
        "description": "2量子ビット: Z + CNOT",
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
    {
        "name": "circuit_2q_h_both_cnot",
        "description": "2量子ビット: 両方にH + CNOT",
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
    
    # ===== 3量子ビット回路 =====
    {
        "name": "circuit_3q_linear",
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
measure q[2] -> c[2];
"""
    },
    {
        "name": "circuit_3q_fan_out",
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
measure q[2] -> c[2];
"""
    },
    {
        "name": "circuit_3q_bell_chain",
        "description": "3量子ビット: Bell状態連鎖",
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
    
    # ===== 4量子ビット回路 =====
    {
        "name": "circuit_4q_ghz",
        "description": "4量子ビット: GHZ状態 (H + 3つのCNOT)",
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
        "description": "4量子ビット: リング構造CNOT",
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
    {
        "name": "circuit_4q_full_entangle",
        "description": "4量子ビット: 全対全エンタングルメント",
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
    
    # ===== 5量子ビット回路 =====
    {
        "name": "circuit_5q_linear",
        "description": "5量子ビット: 線形CNOT連鎖",
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
    
    # ===== 6量子ビット回路 =====
    {
        "name": "circuit_6q_ladder",
        "description": "6量子ビット: ラダー型CNOT",
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
    },
]


def run_trace(name: str, qasm: str) -> dict:
    """APIにトレースリクエストを送信"""
    req_data = json.dumps({"qasm": qasm}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}/trace",
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            elapsed = time.time() - start
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "status": "SUCCESS",
                "elapsed": elapsed,
                "data": data
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            error_detail = error_body.get("detail", str(e))
        except:
            error_detail = str(e)
        return {
            "status": "FAILED",
            "elapsed": elapsed,
            "http_status": e.code,
            "error": error_detail
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "status": "ERROR",
            "elapsed": elapsed,
            "error": str(e)
        }


def main():
    print("=" * 70)
    print("全成功回路 再シミュレーション（logical_qubit_mapping対応版）")
    print(f"総回路数: {len(ALL_SUCCESSFUL_CIRCUITS)}")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 出力ディレクトリ
    output_dir = "final_results"
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    for i, circuit in enumerate(ALL_SUCCESSFUL_CIRCUITS, 1):
        name = circuit["name"]
        desc = circuit["description"]
        qasm = circuit["qasm"]
        
        print(f"\n[{i}/{len(ALL_SUCCESSFUL_CIRCUITS)}] {name}")
        print(f"    説明: {desc}")
        print(f"    開始: {datetime.now().strftime('%H:%M:%S')}")
        print(f"    実行中...", flush=True)
        
        result = run_trace(name, qasm)
        
        if result["status"] == "SUCCESS":
            data = result["data"]["result"]
            meta = data["meta"]
            lq_mapping = data.get("logical_qubit_mapping", [])
            
            # イベント内の変化パッチ数を集計
            total_patch_changes = sum(len(e.get("patch_delta", [])) for e in data["patch"]["events"])
            
            print(f"    ✅ 成功! ({datetime.now().strftime('%H:%M:%S')})")
            print(f"    - グリッド: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
            print(f"    - サイクル: {meta['total_cycles']:,}, 時間: {result['elapsed']:.1f}秒 ({result['elapsed']/60:.1f}分)")
            print(f"    - イベント: {len(data['patch']['events'])}, パッチ変化: {total_patch_changes}")
            
            # データキュービット情報
            data_qubits = [lq for lq in lq_mapping if lq.get("role") == "data"]
            for dq in data_qubits:
                patches = dq.get("patch_indices", [])
                print(f"      q[{dq.get('qubit_index')}] → パッチ {patches}")
            
            results.append({
                "name": name,
                "description": desc,
                "status": "SUCCESS",
                "grid": f"{meta['patch_grid']['rows']}x{meta['patch_grid']['cols']}",
                "num_patches": meta['num_patches'],
                "total_cycles": meta['total_cycles'],
                "elapsed_seconds": round(result['elapsed'], 2),
                "num_events": len(data['patch']['events']),
                "total_patch_changes": total_patch_changes,
                "num_logical_qubits": len(lq_mapping),
                "num_data_qubits": len(data_qubits)
            })
            
            # 結果をファイルに保存
            output_file = f"{output_dir}/{name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"    - 保存: {output_file}")
        else:
            print(f"    ❌ 失敗: {result.get('error', 'Unknown error')}")
            results.append({
                "name": name,
                "description": desc,
                "status": result["status"],
                "error": result.get("error"),
                "elapsed_seconds": round(result['elapsed'], 2)
            })
    
    # サマリー出力
    print("\n" + "=" * 70)
    print("テスト結果サマリー")
    print(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    print(f"成功: {success_count}/{len(results)}")
    
    # グループ化して表示
    for num_q in [2, 3, 4, 5, 6]:
        group = [r for r in results if f"circuit_{num_q}q" in r["name"]]
        if group:
            print(f"\n  === {num_q}量子ビット ===")
            for r in group:
                status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
                if r["status"] == "SUCCESS":
                    print(f"  {status_icon} {r['name']}: {r['grid']}, {r['num_events']}イベント, {r['elapsed_seconds']:.0f}秒")
                else:
                    print(f"  {status_icon} {r['name']}: 失敗")
    
    # サマリーをファイルに保存
    summary = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "version": "final_with_logical_qubit_mapping",
        "total_tests": len(results),
        "passed": success_count,
        "failed": len(results) - success_count,
        "results": results
    }
    with open(f"{output_dir}/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nサマリー保存: {output_dir}/summary.json")
    
    # 総実行時間
    total_time = sum(r.get("elapsed_seconds", 0) for r in results)
    print(f"総実行時間: {total_time:.0f}秒 ({total_time/60:.1f}分, {total_time/3600:.1f}時間)")


if __name__ == "__main__":
    main()


