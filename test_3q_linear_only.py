#!/usr/bin/env python3
"""
3量子ビット線形回路（3q_linear）のテスト
- 修正後の動作確認用
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
import os

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間タイムアウト

# 3量子ビット線形回路
TEST_CIRCUIT = {
    "name": "test_3q_linear",
    "description": "3量子ビット: H + 2つのCNOT",
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


def analyze_gate_mapping(result_data: dict) -> dict:
    """gate_to_event_mappingを分析"""
    gate_mapping = result_data.get("result", {}).get("gate_to_event_mapping", [])
    compiled = result_data.get("result", {}).get("compiled", {})
    events = result_data.get("result", {}).get("patch", {}).get("events", [])
    
    analysis = {
        "has_mapping": len(gate_mapping) > 0,
        "num_gates": len(gate_mapping),
        "gates": [],
        "qisa_count": len(compiled.get("qisa", [])),
        "events_count": len(events),
    }
    
    for gate in gate_mapping:
        gate_info = {
            "gate_idx": gate.get("gate_idx"),
            "gate_type": gate.get("gate_type"),
            "gate_qubits": gate.get("gate_qubits", []),
            "ppr_type": gate.get("ppr_type"),
            "num_events": len(gate.get("events", [])),
            "events": gate.get("events", []),
        }
        analysis["gates"].append(gate_info)
    
    return analysis


def main():
    print("=" * 80)
    print("3量子ビット線形回路 (3q_linear) テスト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 出力ディレクトリ
    output_dir = "test_results_3q_linear"
    os.makedirs(output_dir, exist_ok=True)
    
    circuit = TEST_CIRCUIT
    name = circuit["name"]
    desc = circuit["description"]
    qasm = circuit["qasm"]
    
    print(f"\n回路名: {name}")
    print(f"説明: {desc}")
    print(f"開始時刻: {datetime.now().strftime('%H:%M:%S')}")
    print(f"実行中...（この処理には時間がかかる可能性があります）", flush=True)
    
    result = run_trace(name, qasm)
    
    if result["status"] == "SUCCESS":
        data = result["data"]["result"]
        meta = data["meta"]
        lq_mapping = data.get("logical_qubit_mapping", [])
        
        # gate_to_event_mappingの分析
        analysis = analyze_gate_mapping(result["data"])
        
        # イベント内の変化パッチ数を集計
        total_patch_changes = sum(len(e.get("patch_delta", [])) for e in data["patch"]["events"])
        
        print(f"\n✅ 成功! ({datetime.now().strftime('%H:%M:%S')})")
        print(f"    - 実行時間: {result['elapsed']:.1f}秒 ({result['elapsed']/60:.1f}分)")
        print(f"    - グリッドサイズ: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
        print(f"    - 総サイクル: {meta['total_cycles']:,}")
        print(f"    - イベント数: {len(data['patch']['events'])}")
        print(f"    - 総パッチ変化数: {total_patch_changes}")
        print(f"    - 論理キュービット数: {len(lq_mapping)}")
        print(f"    - QISA命令数: {analysis['qisa_count']}")
        print(f"    - gate_to_event_mapping: {'✅ あり' if analysis['has_mapping'] else '❌ なし'}")
        
        if analysis['has_mapping']:
            print(f"    - マッピングされたゲート数: {analysis['num_gates']}")
            for gate in analysis['gates']:
                print(f"      • ゲート[{gate['gate_idx']}]: {gate['gate_type'].upper()}{gate['gate_qubits']}")
                print(f"        → PPRタイプ: {gate['ppr_type']}, 関連イベント数: {gate['num_events']}")
                if gate['events']:
                    for evt in gate['events']:
                        print(f"          - {evt['inst']} @ cycle {evt['cycle']} (QISA idx: {evt['qisa_idx']})")
        else:
            print(f"    ⚠️ 警告: gate_to_event_mappingが空です")
        
        result_summary = {
            "name": name,
            "description": desc,
            "status": "SUCCESS",
            "grid": f"{meta['patch_grid']['rows']}x{meta['patch_grid']['cols']}",
            "num_patches": meta['num_patches'],
            "total_cycles": meta['total_cycles'],
            "elapsed_seconds": round(result['elapsed'], 2),
            "elapsed_minutes": round(result['elapsed'] / 60, 2),
            "num_events": len(data['patch']['events']),
            "total_patch_changes": total_patch_changes,
            "num_logical_qubits": len(lq_mapping),
            "gate_mapping_available": analysis['has_mapping'],
            "gate_mapping_count": analysis['num_gates'],
            "qisa_count": analysis['qisa_count'],
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
            "test_type": "3q_linear_verification",
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
            "test_type": "3q_linear_verification",
            "circuit": error_summary
        }
        with open(f"{output_dir}/summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()

