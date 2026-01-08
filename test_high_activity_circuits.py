#!/usr/bin/env python3
"""
高活動量（多くのパッチ変化）の量子回路テスト
- 大きなグリッド
- 多数のCNOT操作で多くのマージ/スプリットイベント
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間

# 高活動量の回路定義
TEST_CIRCUITS = [
    {
        "name": "test_10q_all_pairs",
        "description": "10量子ビット: 隣接ペア全てにCNOT（9個のCNOT）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[10];
creg c[10];
h q[0];
h q[2];
h q[4];
h q[6];
h q[8];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
cx q[3],q[4];
cx q[4],q[5];
cx q[5],q[6];
cx q[6],q[7];
cx q[7],q[8];
cx q[8],q[9];
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
    },
    {
        "name": "test_8q_crisscross",
        "description": "8量子ビット: 交差CNOTパターン（多数のマージ/スプリット）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
creg c[8];
h q[0];
h q[1];
h q[2];
h q[3];
cx q[0],q[4];
cx q[1],q[5];
cx q[2],q[6];
cx q[3],q[7];
cx q[4],q[5];
cx q[5],q[6];
cx q[6],q[7];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
measure q[3] -> c[3];
measure q[4] -> c[4];
measure q[5] -> c[5];
measure q[6] -> c[6];
measure q[7] -> c[7];
"""
    },
    {
        "name": "test_12q_wave",
        "description": "12量子ビット: 波状CNOTパターン（大きなグリッド）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[12];
h q[0];
h q[3];
h q[6];
h q[9];
cx q[0],q[1];
cx q[1],q[2];
cx q[3],q[4];
cx q[4],q[5];
cx q[6],q[7];
cx q[7],q[8];
cx q[9],q[10];
cx q[10],q[11];
cx q[2],q[3];
cx q[5],q[6];
cx q[8],q[9];
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
measure q[10] -> c[10];
measure q[11] -> c[11];
"""
    },
    {
        "name": "test_15q_grid_pattern",
        "description": "15量子ビット: グリッドパターンCNOT（最大活動量）",
        "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[15];
creg c[15];
h q[0];
h q[5];
h q[10];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
cx q[3],q[4];
cx q[5],q[6];
cx q[6],q[7];
cx q[7],q[8];
cx q[8],q[9];
cx q[10],q[11];
cx q[11],q[12];
cx q[12],q[13];
cx q[13],q[14];
cx q[0],q[5];
cx q[5],q[10];
cx q[1],q[6];
cx q[6],q[11];
cx q[2],q[7];
cx q[7],q[12];
cx q[3],q[8];
cx q[8],q[13];
cx q[4],q[9];
cx q[9],q[14];
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
measure q[10] -> c[10];
measure q[11] -> c[11];
measure q[12] -> c[12];
measure q[13] -> c[13];
measure q[14] -> c[14];
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
    print("高活動量回路テスト（大グリッド + 多数変化）")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    for i, circuit in enumerate(TEST_CIRCUITS, 1):
        name = circuit["name"]
        desc = circuit["description"]
        qasm = circuit["qasm"]
        
        print(f"\n[{i}/{len(TEST_CIRCUITS)}] {name}")
        print(f"    説明: {desc}")
        print(f"    開始: {datetime.now().strftime('%H:%M:%S')}")
        print(f"    実行中...", flush=True)
        
        result = run_trace(name, qasm)
        
        if result["status"] == "SUCCESS":
            data = result["data"]["result"]
            meta = data["meta"]
            
            # イベント内の変化パッチ数を集計
            total_patch_changes = sum(len(e.get("patch_delta", [])) for e in data["patch"]["events"])
            
            print(f"    ✅ 成功! ({datetime.now().strftime('%H:%M:%S')})")
            print(f"    - グリッドサイズ: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
            print(f"    - 総サイクル: {meta['total_cycles']:,}")
            print(f"    - 実行時間: {result['elapsed']:.1f}秒 ({result['elapsed']/60:.1f}分)")
            print(f"    - イベント数: {len(data['patch']['events'])}")
            print(f"    - 総パッチ変化数: {total_patch_changes}")
            
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
    print(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    print(f"成功: {success_count}/{len(results)}")
    
    for r in results:
        status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
        print(f"  {status_icon} {r['name']}: {r['status']}")
        if r["status"] == "SUCCESS":
            print(f"      グリッド: {r['grid']}, イベント: {r['num_events']}, パッチ変化: {r['total_patch_changes']}")
    
    # サマリーをファイルに保存
    import os
    os.makedirs("test_results_complex", exist_ok=True)
    summary = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "test_type": "high_activity",
        "total_tests": len(results),
        "passed": success_count,
        "failed": len(results) - success_count,
        "results": results
    }
    with open("test_results_complex/summary_high_activity.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nサマリー保存: test_results_complex/summary_high_activity.json")


if __name__ == "__main__":
    main()

