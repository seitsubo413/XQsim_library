#!/usr/bin/env python3
"""
final_resultsフォルダ内のすべての回路を最新版で再シミュレーション
- gate_to_event_mapping情報を含む新バージョン
- すべての回路を再実行して結果を保存
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
import os
import glob

API_URL = "http://localhost:8000"
TIMEOUT = 86400  # 24時間タイムアウト

# final_resultsフォルダからJSONファイルを読み込む
FINAL_RESULTS_DIR = "final_results"


def load_circuits_from_final_results():
    """final_resultsフォルダから回路情報を読み込む"""
    circuits = []
    
    # summary.jsonから回路情報を取得
    summary_path = os.path.join(FINAL_RESULTS_DIR, "summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        
        for result in summary.get("results", []):
            circuit_name = result["name"]
            circuit_json_path = os.path.join(FINAL_RESULTS_DIR, f"{circuit_name}.json")
            
            if os.path.exists(circuit_json_path):
                try:
                    with open(circuit_json_path, "r", encoding="utf-8") as f:
                        circuit_data = json.load(f)
                    
                    # QASMを取得
                    qasm = circuit_data.get("input", {}).get("qasm", "")
                    
                    if qasm:
                        circuits.append({
                            "name": circuit_name,
                            "description": result.get("description", ""),
                            "qasm": qasm
                        })
                        print(f"読み込み: {circuit_name}")
                    else:
                        print(f"警告: {circuit_name} にQASMが見つかりません")
                except Exception as e:
                    print(f"エラー: {circuit_name} の読み込みに失敗: {e}")
    
    return circuits


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
    print("final_results 全回路 再シミュレーション")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 回路を読み込む
    print(f"\n{FINAL_RESULTS_DIR}フォルダから回路を読み込み中...")
    circuits = load_circuits_from_final_results()
    
    if not circuits:
        print("エラー: 回路が見つかりませんでした")
        return
    
    print(f"読み込み完了: {len(circuits)}回路")
    
    # 出力ディレクトリ
    output_dir = "test_results_final_all"
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    for i, circuit in enumerate(circuits, 1):
        name = circuit["name"]
        desc = circuit["description"]
        qasm = circuit["qasm"]
        
        print(f"\n[{i}/{len(circuits)}] {name}")
        print(f"    説明: {desc}")
        print(f"    開始: {datetime.now().strftime('%H:%M:%S')}")
        print(f"    実行中...", flush=True)
        
        result = run_trace(name, qasm)
        
        if result["status"] == "SUCCESS":
            data = result["data"]["result"]
            meta = data["meta"]
            lq_mapping = data.get("logical_qubit_mapping", [])
            
            # gate_to_event_mappingの分析
            analysis = analyze_gate_mapping(result["data"])
            
            # イベント内の変化パッチ数を集計
            total_patch_changes = sum(len(e.get("patch_delta", [])) for e in data["patch"]["events"])
            
            print(f"    ✅ 成功! ({datetime.now().strftime('%H:%M:%S')})")
            print(f"    - 実行時間: {result['elapsed']:.1f}秒 ({result['elapsed']/60:.1f}分)")
            print(f"    - グリッドサイズ: {meta['patch_grid']['rows']}×{meta['patch_grid']['cols']} = {meta['num_patches']}パッチ")
            print(f"    - 総サイクル: {meta['total_cycles']:,}")
            print(f"    - イベント数: {len(data['patch']['events'])}")
            print(f"    - 総パッチ変化数: {total_patch_changes}")
            print(f"    - 論理キュービット数: {len(lq_mapping)}")
            print(f"    - gate_to_event_mapping: {'✅ あり' if analysis['has_mapping'] else '❌ なし'}")
            if analysis['has_mapping']:
                print(f"    - マッピングされたゲート数: {analysis['num_gates']}")
            
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
                "termination_reason": meta.get('termination_reason', 'unknown')
            }
            
            results.append(result_summary)
            
            # 結果をファイルに保存
            output_file = f"{output_dir}/{name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"    - 保存: {output_file}")
        else:
            print(f"    ❌ 失敗: {result.get('error', 'Unknown error')}")
            print(f"    - 実行時間: {result['elapsed']:.1f}秒")
            
            error_summary = {
                "name": name,
                "description": desc,
                "status": result["status"],
                "http_status": result.get("http_status"),
                "error": result.get("error"),
                "elapsed_seconds": round(result['elapsed'], 2)
            }
            results.append(error_summary)
    
    # サマリー出力
    print("\n" + "=" * 80)
    print("テスト結果サマリー")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    mapping_count = sum(1 for r in results if r.get("gate_mapping_available", False))
    
    print(f"成功: {success_count}/{len(results)}")
    print(f"gate_to_event_mappingあり: {mapping_count}/{success_count}")
    
    for r in results:
        status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
        mapping_icon = "✅" if r.get("gate_mapping_available", False) else "❌"
        print(f"  {status_icon} {r['name']}: {r['status']} (マッピング: {mapping_icon})")
    
    # サマリーをファイルに保存
    summary = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "version": "latest_with_gate_mapping",
        "test_type": "final_results_rerun",
        "total_tests": len(results),
        "passed": success_count,
        "failed": len(results) - success_count,
        "mapping_available": mapping_count,
        "results": results
    }
    with open(f"{output_dir}/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nサマリー保存: {output_dir}/summary.json")
    
    print("\n" + "=" * 80)
    print("テスト完了!")
    print("=" * 80)


if __name__ == "__main__":
    main()

