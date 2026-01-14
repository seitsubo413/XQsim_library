# フロントエンド引き継ぎ: Clifford+T回路実行追跡

**作成日**: 2026年1月8日  
**対象**: フロントエンドチーム  
**ステータス**: 実装完了・利用可能

---

## 1. 概要

### 1.1 追加された機能

API レスポンスの JSON に新しいフィールド `clifford_t_execution_trace` が追加されました。
これにより、**Clifford+T回路のすべてのゲートがどのように実行されたか**を追跡できます。

### 1.2 ユースケース

- 各ゲートが「どのパッチ操作に対応するか」を表示
- クリフォードゲート（H, CX, S）が「どのパウリ積・境界に吸収されたか」を表示
- SQM（単一キュービット測定）のサイクル範囲を表示
- 「すべてのゲートが正しく実行された」ことを確認

---

## 2. ゲートの分類

| 種類 | 例 | 実行方法 | サイクル情報 |
|------|-----|----------|-------------|
| **PPR** | T | MERGE/SPLIT操作 | cycle_start, cycle_end |
| **PPM** | Measure（複数キュービット） | MERGE/SPLIT操作 | cycle_start, cycle_end |
| **SQM** | Measure（単一キュービット） | LQM_X/LQM_Z命令 | cycle_after, cycle_before（範囲） |
| **Pauli Frame** | H, CX, S | パウリ積に吸収 | なし（吸収先の情報あり） |

---

## 3. データ構造

### 3.1 レスポンス内の位置

```json
{
  "meta": { ... },
  "input": { ... },
  "compiled": { ... },
  "patch": { ... },
  "logical_qubit_mapping": [ ... ],
  "clifford_t_execution_trace": {    // ← 新規追加
    "gates": [ ... ],
    "summary": { ... }
  }
}
```

### 3.2 gates 配列の要素

#### PPR/PPMゲート（T, Measure複数キュービット）

```json
{
  "gate_idx": 5,
  "gate": "measure",
  "qubits": [0],
  "execution_type": "ppm",
  "pauli_product": ["X", "Z"],
  "target_qubits": [0, 1],
  "cycle_start": 18,
  "cycle_end": 5125
}
```

#### SQMゲート（Measure単一キュービット）

```json
{
  "gate_idx": 8,
  "gate": "measure",
  "qubits": [2],
  "execution_type": "sqm",
  "basis": "X",
  "cycle_after": 39146,
  "cycle_before": 51702
}
```

#### Pauli Frameゲート（H, CX, S）

```json
{
  "gate_idx": 0,
  "gate": "h",
  "qubits": [0],
  "execution_type": "pauli_frame",
  "absorbed_into": [
    {
      "effect": "transform_pauli",
      "pauli_before": "Z",
      "pauli_after": "X",
      "qubit": 0
    }
  ]
}
```

```json
{
  "gate_idx": 1,
  "gate": "cx",
  "qubits": [0, 1],
  "execution_type": "pauli_frame",
  "absorbed_into": [
    {
      "effect": "propagate_pauli",
      "source_qubit": 0,
      "target_qubit": 1,
      "added_pauli": "X"
    }
  ]
}
```

### 3.3 summary

```json
{
  "total_gates": 10,
  "ppr_count": 2,
  "ppm_count": 3,
  "sqm_count": 2,
  "pauli_frame_count": 3,
  "all_gates_traced": true
}
```

---

## 4. フィールド定義

### 4.1 共通フィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `gate_idx` | `number` | Clifford+T回路内でのゲートインデックス（0始まり） |
| `gate` | `string` | ゲート名（小文字）: `h`, `cx`, `s`, `t`, `measure` |
| `qubits` | `number[]` | ゲートが作用するキュービットインデックス |
| `execution_type` | `string` | 実行タイプ: `ppr`, `ppm`, `sqm`, `pauli_frame`, `no_effect` |

### 4.2 PPR/PPM固有フィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `pauli_product` | `string[]` | 最終的なパウリ積 `["X", "Z", "Z"]` |
| `target_qubits` | `number[]` | パウリ積が作用するキュービット |
| `cycle_start` | `number` | MERGE操作のサイクル |
| `cycle_end` | `number` | SPLIT操作のサイクル |

### 4.3 SQM固有フィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `basis` | `string` | 測定基底: `"X"` または `"Z"` |
| `cycle_after` | `number` | このサイクル以降に実行 |
| `cycle_before` | `number` | このサイクル以前に完了 |

### 4.4 Pauli Frame固有フィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `absorbed_into` | `object[]` | 吸収先の情報リスト |

#### absorbed_into の要素

| フィールド | 型 | 説明 |
|-----------|------|------|
| `effect` | `string` | 効果: `transform_pauli` または `propagate_pauli` |
| `pauli_before` | `string?` | 変換前のパウリ（Hの場合） |
| `pauli_after` | `string?` | 変換後のパウリ（Hの場合） |
| `qubit` | `number?` | 対象キュービット（Hの場合） |
| `source_qubit` | `number?` | パウリ伝播元（CXの場合） |
| `target_qubit` | `number?` | パウリ伝播先（CXの場合） |
| `added_pauli` | `string?` | 追加されたパウリ（CXの場合） |

---

## 5. TypeScript 型定義

```typescript
interface CliffordTExecutionTrace {
  gates: GateTraceEntry[];
  summary: {
    total_gates: number;
    ppr_count: number;
    ppm_count: number;
    sqm_count: number;
    pauli_frame_count: number;
    all_gates_traced: boolean;
  };
}

interface GateTraceEntry {
  gate_idx: number;
  gate: string;
  qubits: number[];
  execution_type: 'ppr' | 'ppm' | 'sqm' | 'pauli_frame' | 'no_effect';
  
  // PPR/PPM
  pauli_product?: string[];
  target_qubits?: number[];
  cycle_start?: number;
  cycle_end?: number;
  
  // SQM
  basis?: 'X' | 'Z';
  cycle_after?: number;
  cycle_before?: number;
  
  // Pauli Frame
  absorbed_into?: AbsorptionInfo[];
}

interface AbsorptionInfo {
  effect: 'transform_pauli' | 'propagate_pauli';
  pauli_before?: string;
  pauli_after?: string;
  qubit?: number;
  source_qubit?: number;
  target_qubit?: number;
  added_pauli?: string;
}
```

---

## 6. フロントエンド実装例

### 6.1 ゲート状態の表示

```typescript
function getGateStatusLabel(entry: GateTraceEntry): string {
  switch (entry.execution_type) {
    case 'ppr':
      return `PPR (T gate) @ cycle ${entry.cycle_start}-${entry.cycle_end}`;
    case 'ppm':
      return `PPM (Measure) @ cycle ${entry.cycle_start}-${entry.cycle_end}`;
    case 'sqm':
      return `SQM (${entry.basis} basis) @ cycle ${entry.cycle_after}-${entry.cycle_before}`;
    case 'pauli_frame':
      return `Pauli Frame (absorbed)`;
    default:
      return 'No effect';
  }
}
```

### 6.2 クリフォードゲートの吸収先表示

```typescript
function formatAbsorption(info: AbsorptionInfo): string {
  if (info.effect === 'transform_pauli') {
    return `q[${info.qubit}]: ${info.pauli_before} → ${info.pauli_after}`;
  } else {
    return `q[${info.source_qubit}] → q[${info.target_qubit}]: +${info.added_pauli}`;
  }
}
```

### 6.3 サイクル進行に応じたゲート状態

```typescript
function getGateStateAtCycle(
  trace: CliffordTExecutionTrace,
  cycle: number
): { executing: GateTraceEntry[]; completed: GateTraceEntry[] } {
  const executing: GateTraceEntry[] = [];
  const completed: GateTraceEntry[] = [];
  
  for (const gate of trace.gates) {
    if (gate.execution_type === 'ppr' || gate.execution_type === 'ppm') {
      if (gate.cycle_start && gate.cycle_end) {
        if (cycle >= gate.cycle_start && cycle <= gate.cycle_end) {
          executing.push(gate);
        } else if (cycle > gate.cycle_end) {
          completed.push(gate);
        }
      }
    } else if (gate.execution_type === 'sqm') {
      if (gate.cycle_after && gate.cycle_before) {
        if (cycle >= gate.cycle_after && cycle <= gate.cycle_before) {
          executing.push(gate);
        } else if (cycle > gate.cycle_before) {
          completed.push(gate);
        }
      }
    } else if (gate.execution_type === 'pauli_frame') {
      // Pauli frameゲートは最初のPPM/PPRより前に完了
      completed.push(gate);
    }
  }
  
  return { executing, completed };
}
```

---

## 7. 表示例

### 回路の実行追跡表示

```
Clifford+T回路: 6ゲート

├─ [0] H q[0]
│   └─ Pauli Frame: q[0] の Z → X に変換
│   └─ PPM#0 に吸収
│
├─ [1] CX q[0],q[1]
│   └─ Pauli Frame: q[0] → q[1] にパウリ X を伝播
│   └─ PPM#0 に吸収
│
├─ [2] Measure q[0]
│   └─ PPM#0: サイクル 18 〜 5125
│   └─ パウリ積: [X, Z]
│   └─ 対象: q[0], q[1]
│
├─ [3] CX q[1],q[2]
│   └─ Pauli Frame: q[1] → q[2] にパウリ Z を伝播
│   └─ PPM#1 に吸収
│
├─ [4] Measure q[1]
│   └─ PPM#1: サイクル 10750 〜 16463
│
└─ [5] Measure q[2]
    └─ SQM: X基底
    └─ サイクル 39146 〜 51702

✅ すべてのゲート (6/6) の実行を確認
```

---

## 8. 注意点

### 8.1 Pauli Frameゲートのタイミング

Pauli Frameゲート（H, CX, S）は物理的な操作を生成しないため、明確なサイクル情報がありません。
これらのゲートは「次のPPM/PPRより前に論理的に完了している」と解釈してください。

### 8.2 SQMのサイクル範囲

SQMは境界操作を生成しないため、正確なサイクルではなく範囲（cycle_after 〜 cycle_before）で表示されます。

### 8.3 all_gates_traced

`summary.all_gates_traced` が `true` の場合、すべてのゲートが何らかの形で追跡されています。

---

## 9. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-01-08 | 初版作成。`clifford_t_execution_trace` フィールドを追加 |
