#!/usr/bin/env python3
"""
単一の高活動量回路テスト: 13量子ビット（上限）グリッドパターン
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間

CIRCUIT = {
    "name": "test_13q_max_grid",
    "description": "13量子ビット（上限）: グリッドパターンCNOT（多数のマージ/スプリット）",
    "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[13];
creg c[13];
h q[0];
h q[4];
h q[8];
h q[12];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
cx q[4],q[5];
cx q[5],q[6];
cx q[6],q[7];
cx q[8],q[9];
cx q[9],q[10];
cx q[10],q[11];
cx q[11],q[12];
cx q[0],q[4];
cx q[4],q[8];
cx q[1],q[5];
cx q[5],q[9];
cx q[2],q[6];
cx q[6],q[10];
cx q[3],q[7];
cx q[7],q[11];
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
"""
}


def main():
    print("=" * 60)
    print("高活動量回路テスト: 13量子ビット（上限）グリッドパターン")
    print(f"予想グリッド: 3×8 = 24パッチ")
    print(f"CNOT数: 18個")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    name = CIRCUIT["name"]
    qasm = CIRCUIT["qasm"]
    
    print(f"\n実行中...", flush=True)
    
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
            data = json.loads(resp.read().decode("utf-8"))["result"]
            
            meta = data["meta"]
            total_patch_changes = sum(len(e.get("patch_delta", [])) for e in data["patch"]["events"])
            
            print(f"\n✅ 成功!")
            print(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\n--- 結果 ---")
            print(f"グリッドサイズ: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
            print(f"総サイクル: {meta['total_cycles']:,}")
            print(f"実行時間: {elapsed:.1f}秒 ({elapsed/60:.1f}分)")
            print(f"イベント数: {len(data['patch']['events'])}")
            print(f"総パッチ変化数: {total_patch_changes}")
            
            # 各イベントの詳細
            print(f"\n--- イベント詳細 ---")
            for e in data["patch"]["events"]:
                print(f"  サイクル {e['cycle']}: {e['inst']} - {len(e['patch_delta'])}パッチ変化")
            
            # 保存
            import os
            os.makedirs("test_results_complex", exist_ok=True)
            with open(f"test_results_complex/{name}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n保存: test_results_complex/{name}.json")
            
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            print(f"\n❌ 失敗: {error_body.get('detail', str(e))}")
        except:
            print(f"\n❌ 失敗: {e}")
        print(f"経過時間: {elapsed:.1f}秒")
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ 失敗: {e}")
        print(f"経過時間: {elapsed:.1f}秒")


if __name__ == "__main__":
    main()
