#!/usr/bin/env python3
"""
超大規模・超複雑な量子回路のテストスクリプト
- 20量子ビット以上
- 100ゲート以上
- 複数のエンタングルメントパターンを組み合わせ
- 様々なゲートタイプを含む
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
import os

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間タイムアウト

# 超大規模・超複雑な回路定義
# 量子ビット数は上限内（12量子ビット）に抑え、ゲート数を最大化
TEST_CIRCUIT = {
    "name": "test_12q_ultra_complex",
    "description": "12量子ビット: 超複雑回路（多数のゲート、深いエンタングルメント、複数のパターン組み合わせ）",
    "qasm": """OPENQASM 2.0;
include "qelib1.inc";
qreg q[12];
creg c[12];

// ===== フェーズ1: 初期化とGHZ状態の作成（0-3） =====
h q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
h q[1];
h q[2];
h q[3];

// ===== フェーズ2: リング構造のエンタングルメント（4-7） =====
h q[4];
cx q[4],q[5];
cx q[5],q[6];
cx q[6],q[7];
cx q[7],q[4];  // リングを閉じる
h q[5];
h q[6];
h q[7];

// ===== フェーズ3: ラダー型エンタングルメント（8-11） =====
h q[8];
h q[9];
cx q[8],q[10];
cx q[9],q[11];
cx q[10],q[11];
h q[10];
h q[11];

// ===== フェーズ4: グループ間のクロスエンタングルメント =====
cx q[0],q[4];
cx q[1],q[5];
cx q[2],q[6];
cx q[3],q[7];
cx q[4],q[8];
cx q[5],q[9];
cx q[6],q[10];
cx q[7],q[11];

// ===== フェーズ5: 単一量子ビットゲートの多様な適用 =====
h q[0];
h q[2];
h q[4];
h q[6];
h q[8];
h q[10];
x q[1];
x q[3];
x q[5];
x q[7];
x q[9];
x q[11];
z q[0];
z q[2];
z q[4];
z q[6];
z q[8];
z q[10];
t q[1];
t q[3];
t q[5];
t q[7];
t q[9];
t q[11];
tdg q[0];
tdg q[2];
tdg q[4];
tdg q[6];
tdg q[8];
tdg q[10];

// ===== フェーズ6: 追加のCNOT操作でエンタングルメントを強化 =====
cx q[0],q[6];
cx q[1],q[7];
cx q[2],q[8];
cx q[3],q[9];
cx q[4],q[10];
cx q[5],q[11];
cx q[0],q[8];
cx q[1],q[9];
cx q[2],q[10];
cx q[3],q[11];
cx q[4],q[0];
cx q[5],q[1];
cx q[6],q[2];
cx q[7],q[3];

// ===== フェーズ7: 逆方向のCNOTで複雑さを増す =====
cx q[11],q[5];
cx q[10],q[4];
cx q[9],q[3];
cx q[8],q[2];
cx q[7],q[1];
cx q[6],q[0];
cx q[5],q[11];
cx q[4],q[10];
cx q[3],q[9];
cx q[2],q[8];
cx q[1],q[7];
cx q[0],q[6];

// ===== フェーズ8: 対角線パターンのCNOT =====
cx q[0],q[5];
cx q[1],q[6];
cx q[2],q[7];
cx q[3],q[8];
cx q[4],q[9];
cx q[5],q[10];
cx q[6],q[11];
cx q[0],q[7];
cx q[1],q[8];
cx q[2],q[9];
cx q[3],q[10];
cx q[4],q[11];

// ===== フェーズ9: さらなる単一量子ビットゲート =====
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
h q[10];
h q[11];
x q[0];
x q[2];
x q[4];
x q[6];
x q[8];
x q[10];
z q[1];
z q[3];
z q[5];
z q[7];
z q[9];
z q[11];

// ===== フェーズ10: 複雑なCNOTパターン（全対全エンタングルメントの一部） =====
cx q[0],q[1];
cx q[0],q[2];
cx q[0],q[3];
cx q[1],q[2];
cx q[1],q[3];
cx q[2],q[3];
cx q[4],q[5];
cx q[4],q[6];
cx q[4],q[7];
cx q[5],q[6];
cx q[5],q[7];
cx q[6],q[7];
cx q[8],q[9];
cx q[8],q[10];
cx q[8],q[11];
cx q[9],q[10];
cx q[9],q[11];
cx q[10],q[11];

// ===== フェーズ11: グループ間の最終エンタングルメント =====
cx q[0],q[4];
cx q[0],q[8];
cx q[1],q[5];
cx q[1],q[9];
cx q[2],q[6];
cx q[2],q[10];
cx q[3],q[7];
cx q[3],q[11];
cx q[4],q[8];
cx q[5],q[9];
cx q[6],q[10];
cx q[7],q[11];

// ===== フェーズ12: 最終的な単一量子ビットゲート =====
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
h q[10];
h q[11];
t q[0];
t q[1];
t q[2];
t q[3];
t q[4];
t q[5];
t q[6];
t q[7];
t q[8];
t q[9];
t q[10];
t q[11];
tdg q[0];
tdg q[1];
tdg q[2];
tdg q[3];
tdg q[4];
tdg q[5];
tdg q[6];
tdg q[7];
tdg q[8];
tdg q[9];
tdg q[10];
tdg q[11];

// ===== フェーズ13: 最後のCNOT操作 =====
cx q[0],q[11];
cx q[1],q[10];
cx q[2],q[9];
cx q[3],q[8];
cx q[4],q[7];
cx q[5],q[6];
cx q[6],q[5];
cx q[7],q[4];
cx q[8],q[3];
cx q[9],q[2];
cx q[10],q[1];
cx q[11],q[0];

// ===== フェーズ14: 最終的なHゲートと測定 =====
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
h q[10];
h q[11];

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
}


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
    print("=" * 80)
    print("超大規模・超複雑な量子回路テスト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 出力ディレクトリ
    output_dir = "test_results_large"
    os.makedirs(output_dir, exist_ok=True)
    
    circuit = TEST_CIRCUIT
    name = circuit["name"]
    desc = circuit["description"]
    qasm = circuit["qasm"]
    
    # ゲート数をカウント
    gate_count = qasm.count("h ") + qasm.count("cx ") + qasm.count("x ") + \
                 qasm.count("z ") + qasm.count("t ") + qasm.count("tdg ") + \
                 qasm.count("measure ")
    
    print(f"\n回路名: {name}")
    print(f"説明: {desc}")
    print(f"量子ビット数: 12")
    print(f"推定ゲート数: {gate_count}以上")
    print(f"開始時刻: {datetime.now().strftime('%H:%M:%S')}")
    print(f"実行中...（この処理には時間がかかる可能性があります）", flush=True)
    
    result = run_trace(name, qasm)
    
    if result["status"] == "SUCCESS":
        data = result["data"]["result"]
        meta = data["meta"]
        lq_mapping = data.get("logical_qubit_mapping", [])
        
        # イベント内の変化パッチ数を集計
        total_patch_changes = sum(len(e.get("patch_delta", [])) for e in data["patch"]["events"])
        
        print(f"\n✅ 成功! ({datetime.now().strftime('%H:%M:%S')})")
        print(f"    - グリッドサイズ: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
        print(f"    - 総サイクル: {meta['total_cycles']:,}")
        print(f"    - 実行時間: {result['elapsed']:.1f}秒 ({result['elapsed']/60:.1f}分)")
        print(f"    - イベント数: {len(data['patch']['events'])}")
        print(f"    - 総パッチ変化数: {total_patch_changes}")
        print(f"    - 論理キュービット数: {len(lq_mapping)}")
        
        # 論理キュービットマッピングの簡易表示
        data_qubits = [lq for lq in lq_mapping if lq.get("role") == "data"]
        print(f"    - データキュービット: {len(data_qubits)}個")
        
        result_summary = {
            "name": name,
            "description": desc,
            "status": "SUCCESS",
            "num_qubits": 12,
            "estimated_gates": gate_count,
            "grid": f"{meta['patch_grid']['rows']}x{meta['patch_grid']['cols']}",
            "num_patches": meta['num_patches'],
            "total_cycles": meta['total_cycles'],
            "elapsed_seconds": round(result['elapsed'], 2),
            "elapsed_minutes": round(result['elapsed'] / 60, 2),
            "num_events": len(data['patch']['events']),
            "total_patch_changes": total_patch_changes,
            "num_logical_qubits": len(lq_mapping),
            "num_data_qubits": len(data_qubits),
            "termination_reason": meta.get('termination_reason', 'unknown')
        }
        
        # 結果をファイルに保存
        output_file = f"{output_dir}/{name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"    - 保存: {output_file}")
        
        # サマリーをファイルに保存
        summary = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "test_type": "ultra_large_complex",
            "circuit": result_summary
        }
        with open(f"{output_dir}/summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"    - サマリー保存: {output_dir}/summary.json")
        
        print("\n" + "=" * 80)
        print("テスト完了!")
        print("=" * 80)
    else:
        print(f"\n❌ 失敗: {result.get('error', 'Unknown error')}")
        print(f"    - 実行時間: {result['elapsed']:.1f}秒")
        
        error_summary = {
            "name": name,
            "description": desc,
            "status": result["status"],
            "http_status": result.get("http_status"),
            "error": result.get("error"),
            "elapsed_seconds": round(result['elapsed'], 2)
        }
        
        summary = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "test_type": "ultra_large_complex",
            "circuit": error_summary
        }
        with open(f"{output_dir}/summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()

