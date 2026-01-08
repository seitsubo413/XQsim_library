# 回路-パッチイベント対応マッピング実装計画書

**作成日**: 2026年1月8日  
**ステータス**: 承認済み  
**予定工数**: 5-8日

---

## 1. 概要

### 1.1 目的

ビジュアライザーフロントエンドにおいて、パッチの変化と同時に「Clifford+T回路のどのゲートが実行中か」をハイライト表示できるよう、JSONにマッピング情報を追加する。

### 1.2 スコープ

#### 実装する機能（In Scope）

| 機能 | 説明 |
|-----|------|
| Clifford+T → PPR対応 | 各Clifford+TゲートがどのPPR/PPM操作に属するかを追跡 |
| PPR → イベント対応 | 各PPR/PPM操作がどのMERGE_INFO/SPLIT_INFOイベントに対応するかを記録 |
| JSON出力拡張 | 上記マッピング情報を`compilation_trace`フィールドとして出力 |

#### 実装しない機能（Out of Scope）

| 機能 | 除外理由 |
|-----|---------|
| 元QASM → Clifford+T対応 | pytket最適化により正確な追跡が不可能 |
| 推定ベースのマッピング | 方針として推定処理は使用しない |
| 元QASM→Clifford+T変換アニメーション用データ | 上記理由により提供不可 |

---

## 2. 技術設計

### 2.1 データフロー

```
[gsc_compiler.py]
    │
    ├─ decompose_Clifford_T_to_PPR()
    │   └─ construct_one_block()  ← 修正: ゲート→PPR対応を記録
    │
    └─ qisa_compile()  ← 修正: PPR→QISA対応を記録

[patch_trace_backend.py]
    │
    └─ trace_patches_from_qasm()  ← 修正: マッピング情報をJSONに追加
```

### 2.2 新規データ構造

#### 2.2.1 PPR/PPM操作情報

```python
@dataclass
class PPROperation:
    ppr_idx: int                    # PPR/PPM操作の連番
    op_type: str                    # "PPR" or "PPM" or "SQM"
    pauli_product: List[str]        # ["Z", "X", "Y", ...] 
    sign: str                       # "+" or "-"
    target_qubits: List[int]        # [0, 1, 3, ...]
    source_gate_indices: List[int]  # Clifford+T回路内のゲートインデックス
```

#### 2.2.2 イベントマッピング情報

```python
@dataclass
class EventMapping:
    event_seq: int          # patch.events内のseq番号
    event_inst: str         # "MERGE_INFO" or "SPLIT_INFO" or "PREP_INFO"
    ppr_idx: int            # 対応するPPR操作のインデックス
    qisa_line_idx: int      # compiled.qisa内の行番号
```

### 2.3 出力JSONフォーマット

```json
{
  "meta": { ... },
  "input": { ... },
  "compiled": {
    "clifford_t_qasm": "...",
    "clifford_t_gates": [
      { "idx": 0, "gate": "h", "qubits": [0] },
      { "idx": 1, "gate": "cx", "qubits": [0, 1] },
      { "idx": 2, "gate": "t", "qubits": [0] }
    ],
    "qisa": [ ... ],
    "qbin_name": "..."
  },
  "compilation_trace": {
    "ppr_operations": [
      {
        "ppr_idx": 0,
        "op_type": "PPR",
        "pauli_product": ["Y", "Z", "Z", "X"],
        "sign": "+",
        "target_qubits": [0, 1, 2, 3],
        "source_gate_indices": [0, 1, 2, 5, 8],
        "qisa_start_idx": 0,
        "qisa_end_idx": 11
      }
    ],
    "event_to_ppr_mapping": [
      {
        "event_seq": 0,
        "event_inst": "MERGE_INFO",
        "ppr_idx": 0,
        "qisa_line_idx": 3
      },
      {
        "event_seq": 1,
        "event_inst": "SPLIT_INFO", 
        "ppr_idx": 0,
        "qisa_line_idx": 8
      }
    ]
  },
  "patch": { ... }
}
```

---

## 3. 実装ステップ

### Phase 1: Clifford+T → PPR対応の追跡（2-3日）

#### Step 1.1: Clifford+Tゲートリストの生成

**ファイル**: `src/compiler/gsc_compiler.py`

- `decompose_qc_to_Clifford_T()`の戻り値を拡張
- 回路内の各ゲートに連番インデックスを付与
- ゲート情報（種類、対象qubit）をリストとして返却

#### Step 1.2: construct_one_block()の修正

**ファイル**: `src/compiler/gsc_compiler.py`

- 関数シグネチャを拡張し、参照したゲートのインデックスを記録
- 戻り値に`source_gate_indices`を追加

#### Step 1.3: decompose_Clifford_T_to_PPR()の修正

**ファイル**: `src/compiler/gsc_compiler.py`

- PPR/PPMリストに`source_gate_indices`を含める
- ゲートリストも併せて返却

### Phase 2: PPR → QISA/イベント対応の追跡（1-2日）

#### Step 2.1: qisa_compile()の修正

**ファイル**: `src/compiler/gsc_compiler.py`

- 各PPR/PPMに対して生成したQISA行のインデックス範囲を記録
- MERGE_INFO/SPLIT_INFOの行番号を特定

#### Step 2.2: コンパイル結果のエクスポート

**ファイル**: `src/compiler/gsc_compiler.py`

- 新規関数`get_compilation_trace()`を追加
- PPR操作リストとQISA対応情報を返却

### Phase 3: JSON出力の拡張（1日）

#### Step 3.1: patch_trace_backend.pyの修正

**ファイル**: `src/patch_trace_backend.py`

- `trace_patches_from_qasm()`内でコンパイル情報を取得
- `compilation_trace`フィールドを応答JSONに追加
- `compiled.clifford_t_gates`フィールドを追加

#### Step 3.2: イベントとPPRの紐付け

**ファイル**: `src/patch_trace_backend.py`

- シミュレーション実行時に、各イベントのqisa_idxからPPR_idxを逆引き
- `event_to_ppr_mapping`を生成

### Phase 4: テスト・検証（1-2日）

#### Step 4.1: 単体テスト

- 各PPRが正しいゲートインデックスを参照しているか確認
- QISA行番号が正しく記録されているか確認

#### Step 4.2: 統合テスト

- 既存のテストケース（2q, 3q回路）で新フォーマットを生成
- フロントエンドチームと連携して動作確認

---

## 4. 修正対象ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/compiler/gsc_compiler.py` | PPR追跡、QISA対応記録 |
| `src/patch_trace_backend.py` | JSON出力拡張 |
| `docs/API_OUTPUT_FORMAT.md` | 仕様書更新 |
| `docs/types/xqsim.d.ts` | TypeScript型定義更新（必要に応じて） |

---

## 5. スケジュール

| 日程 | 作業内容 |
|-----|---------|
| Day 1-2 | Phase 1: construct_one_block()修正、ゲート追跡実装 |
| Day 3 | Phase 1完了、Phase 2: qisa_compile()修正 |
| Day 4 | Phase 2完了、Phase 3: JSON出力拡張 |
| Day 5 | Phase 3完了、Phase 4: テスト開始 |
| Day 6-7 | Phase 4: 統合テスト、バグ修正 |
| Day 8 | ドキュメント更新、リリース準備 |

---

## 6. リスクと対策

| リスク | 影響度 | 対策 |
|-------|-------|------|
| Clifford+T分解ロジックの複雑さ | 中 | 段階的な実装とテストで品質確保 |
| 既存テストへの影響 | 低 | 新フィールドは追加のみ、既存構造は維持 |
| フロントエンドとの仕様齟齬 | 中 | 早期にサンプルJSONを共有し確認 |

---

## 7. 成果物

1. 修正済みソースコード
2. 更新されたAPI仕様書
3. サンプル出力JSON
4. テスト結果レポート

---

## 8. 備考

### 8.1 フロントエンド連携事項

- Phase 3完了後にサンプルJSONを提供予定
- フォーマットの微調整は随時対応可能

### 8.2 将来の拡張可能性

現在の設計では以下の拡張が可能：
- PPR内の個別ゲートへの実行進捗表示（必要に応じて粒度を細かくできる）
- 複数のイベント種類への対応拡張

---

**承認者**: （フロントエンドチーム）  
**実装担当**: （バックエンドチーム）

