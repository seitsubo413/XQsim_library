#!/usr/bin/env python3
"""
複雑な量子回路のテストスクリプト
5つ以上の回路をテストして、成功・失敗を記録する
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime

API_URL = "http://localhost:8000"
TIMEOUT = 3600  # 1時間タイムアウト

# テスト回路の定義
TEST_CIRCUITS = [
    {
        "name": "test_4q_ghz",
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
        "name": "test_5q_linear",
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
    {
        "name": "test_4q_ring",
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
        "name": "test_3q_toffoli_decomposed",
        "description": "3量子ビット: Toffoliゲート分解 (H, T, Tdg, CNOT)",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[2];
cx q[1],q[2];
tdg q[2];
cx q[0],q[2];
t q[2];
cx q[1],q[2];
tdg q[2];
cx q[0],q[2];
t q[1];
t q[2];
h q[2];
cx q[0],q[1];
t q[0];
tdg q[1];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
"""
    },
    {
        "name": "test_6q_ladder",
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
    {
        "name": "test_4q_full_entangle",
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
    print("=" * 60)
    print("複雑な量子回路テスト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    for i, circuit in enumerate(TEST_CIRCUITS, 1):
        name = circuit["name"]
        desc = circuit["description"]
        qasm = circuit["qasm"]
        
        print(f"\n[{i}/{len(TEST_CIRCUITS)}] {name}")
        print(f"    説明: {desc}")
        print(f"    実行中...", flush=True)
        
        result = run_trace(name, qasm)
        
        if result["status"] == "SUCCESS":
            data = result["data"]["result"]
            meta = data["meta"]
            print(f"    ✅ 成功!")
            print(f"    - グリッドサイズ: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
            print(f"    - 総サイクル: {meta['total_cycles']:,}")
            print(f"    - 実行時間: {result['elapsed']:.1f}秒 ({result['elapsed']/60:.1f}分)")
            print(f"    - イベント数: {len(data['patch']['events'])}")
            
            results.append({
                "name": name,
                "description": desc,
                "status": "SUCCESS",
                "grid": f"{meta['patch_grid']['rows']}x{meta['patch_grid']['cols']}",
                "num_patches": meta['num_patches'],
                "total_cycles": meta['total_cycles'],
                "elapsed_seconds": round(result['elapsed'], 2),
                "num_events": len(data['patch']['events']),
                "termination_reason": meta.get('termination_reason', 'unknown')
            })
            
            # 結果をファイルに保存
            output_file = f"test_results_complex/{name}.json"
            import os
            os.makedirs("test_results_complex", exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"    - 保存: {output_file}")
        else:
            print(f"    ❌ 失敗: {result.get('error', 'Unknown error')}")
            results.append({
                "name": name,
                "description": desc,
                "status": result["status"],
                "http_status": result.get("http_status"),
                "error": result.get("error"),
                "elapsed_seconds": round(result['elapsed'], 2)
            })
    
    # サマリー出力
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    print(f"成功: {success_count}/{len(results)}")
    
    for r in results:
        status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
        print(f"  {status_icon} {r['name']}: {r['status']}")
        if r["status"] == "SUCCESS":
            print(f"      グリッド: {r['grid']}, サイクル: {r['total_cycles']:,}, 時間: {r['elapsed_seconds']:.1f}秒")
    
    # サマリーをファイルに保存
    import os
    os.makedirs("test_results_complex", exist_ok=True)
    summary = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_tests": len(results),
        "passed": success_count,
        "failed": len(results) - success_count,
        "results": results
    }
    with open("test_results_complex/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nサマリー保存: test_results_complex/summary.json")


if __name__ == "__main__":
    main()

