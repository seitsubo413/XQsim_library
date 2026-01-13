#!/usr/bin/env python3
"""
ゲート→パッチイベント対応付けのテスト
"""

import json
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from patch_trace_backend import trace_patches_from_qasm

# シンプルな3量子ビット回路
TEST_QASM = """OPENQASM 2.0;
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
measure q[2] -> c[2];
"""

def main():
    print("=" * 70)
    print("ゲート→パッチイベント対応付けテスト")
    print("=" * 70)
    
    print("\n実行中...")
    try:
        result = trace_patches_from_qasm(
            TEST_QASM,
            config_name="example_cmos_d5",
            skip_pqsim=True,
            num_shots=1,
            keep_artifacts=False,
            debug_logging=False,
            max_cycles=100_000,
            timeout_seconds=300,
        )
        
        print("✅ 成功!")
        
        # 基本情報
        meta = result["meta"]
        print(f"\n--- 基本情報 ---")
        print(f"グリッドサイズ: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
        print(f"総サイクル: {meta['total_cycles']:,}")
        print(f"実行時間: {meta['elapsed_seconds']:.1f}秒")
        print(f"イベント数: {len(result['patch']['events'])}")
        
        # ゲート→イベントマッピング
        gate_mapping = result.get("gate_to_event_mapping", [])
        print(f"\n--- ゲート→イベントマッピング ---")
        print(f"マッピング数: {len(gate_mapping)}")
        
        if gate_mapping:
            print("\n最初の5つのマッピング:")
            for i, gm in enumerate(gate_mapping[:5], 1):
                print(f"\n{i}. Gate #{gm['gate_idx']}: {gm['gate_type']} q{gm['gate_qubits']}")
                print(f"   PPR/PPM: {gm['ppr_type']} (idx={gm['ppr_idx']})")
                print(f"   QISA行: {gm['qisa_start_idx']} - {gm['qisa_end_idx']}")
                events = gm.get("events", [])
                print(f"   イベント数: {len(events)}")
                for evt in events:
                    print(f"     - Seq {evt['seq']}: {evt['inst']} (qisa_idx={evt['qisa_idx']}, cycle={evt['cycle']})")
        else:
            print("⚠️  マッピングが空です")
        
        # 論理キュービットマッピング
        lq_mapping = result.get("logical_qubit_mapping", [])
        print(f"\n--- 論理キュービットマッピング ---")
        print(f"論理キュービット数: {len(lq_mapping)}")
        data_qubits = [lq for lq in lq_mapping if lq.get("role") == "data"]
        print(f"データキュービット数: {len(data_qubits)}")
        
        # 結果を保存
        output_file = "test_results/gate_mapping_test.json"
        os.makedirs("test_results", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n結果を保存: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
