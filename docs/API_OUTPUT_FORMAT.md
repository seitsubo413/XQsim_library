# XQsim Patch Trace API - 出力フォーマット仕様書

**バージョン**: 3  
**最終更新**: 2024年12月

---

## 概要

このドキュメントは、XQsim Patch Trace API (`POST /trace`) のレスポンス形式を定義します。
フロントエンド開発者がパッチの可視化を実装する際の参照資料として使用してください。

---

## エンドポイント

```
POST /trace
Content-Type: application/json
```

### リクエスト

```json
{
  "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\n...",
  "config": "example_cmos_d5"
}
```

---

## レスポンス構造

```
{
  "result": {
    "meta": { ... },      // メタデータ
    "input": { ... },     // 入力情報
    "compiled": { ... },  // コンパイル結果
    "patch": {            // パッチデータ（メイン）
      "initial": [...],   // 初期状態
      "events": [...]     // 時系列イベント
    }
  }
}
```

---

## 1. meta（メタデータ）

シミュレーションの概要情報。

```typescript
interface Meta {
  version: number;              // APIバージョン (現在: 3)
  config: string;               // 使用した設定名
  block_type: string;           // ブロックタイプ ("Distillation" など)
  code_distance: number;        // 表面符号の距離 (例: 5)
  patch_grid: {
    rows: number;               // パッチグリッドの行数
    cols: number;               // パッチグリッドの列数
  };
  num_patches: number;          // 総パッチ数 (rows × cols)
  total_cycles: number;         // シミュレーション総サイクル数
  elapsed_seconds: number;      // 実行時間（秒）
  termination_reason: string;   // 終了理由 ("normal" | "timeout" | "max_cycles")
  forced_terminations: string[];// 強制終了の記録
  stability_check_failures: string[]; // 安定性チェック失敗の記録
  warnings: string[];           // 警告メッセージ
}
```

### 例

```json
{
  "version": 3,
  "config": "example_cmos_d5",
  "block_type": "Distillation",
  "code_distance": 5,
  "patch_grid": { "rows": 3, "cols": 4 },
  "num_patches": 12,
  "total_cycles": 17672,
  "elapsed_seconds": 514.11,
  "termination_reason": "normal",
  "forced_terminations": [],
  "stability_check_failures": [],
  "warnings": ["Padding applied: original 2 qubits -> 3 qubits for compilation."]
}
```

---

## 2. input（入力情報）

入力されたQASMと量子ビット数の情報。

```typescript
interface Input {
  qasm: string;                 // 入力QASM（元のまま）
  num_qasm_qubits: number;      // 元のQASMの量子ビット数
  num_compile_qubits: number;   // コンパイル時の量子ビット数
  padding_applied: boolean;     // パディングが適用されたか
}
```

### 注意事項

- XQsimは最低3量子ビットを必要とするため、2量子ビット以下の回路は自動的にパディングされます
- `padding_applied: true` の場合、`warnings` にパディングの詳細が記載されます

---

## 3. compiled（コンパイル結果）

QASM → QISA への変換結果。

```typescript
interface Compiled {
  clifford_t_qasm: string;           // Clifford+Tゲートに変換されたQASM
  clifford_t_qasm_padded: string | null; // パディング適用後のQASM（適用時のみ）
  qisa: string[];                    // QISA命令リスト
  qbin_name: string;                 // 生成されたバイナリ名
}
```

### QISA命令の例

```json
[
  "PREP_INFO     NA   NA    NA   NA",
  "LQI           NA   NA    0x00 [-,-,T,T,T,-,-,-,-,-,-,-,-,-,-,-,]",
  "RUN_ESM       NA   NA    NA   NA",
  "MERGE_INFO    NA   NA    0x00 [I,I,X,Z,I,I,I,I,I,I,I,I,I,I,I,I,]",
  "INIT_INTMD    NA   NA    NA   NA",
  "RUN_ESM       NA   NA    NA   NA",
  "PPM_INTERPRET +TTN 0x001 0x00 [I,I,X,Z,I,I,I,I,I,I,I,I,I,I,I,I,]",
  "MEAS_INTMD    NA   NA    NA   NA",
  "SPLIT_INFO    NA   NA    NA   NA",
  "RUN_ESM       NA   NA    NA   NA",
  "LQM_X         +FTN 0x002 0x00 [-,-,T,-,-,-,-,-,-,-,-,-,-,-,-,-,]"
]
```

---

## 4. patch（パッチデータ）★重要★

フロントエンドでの可視化に使用するメインデータ。

### 4.1 initial（初期状態）

シミュレーション開始時の全パッチの状態。

```typescript
interface Patch {
  pchidx: number;     // パッチインデックス (0〜num_patches-1)
  row: number;        // グリッド上の行位置 (0-indexed)
  col: number;        // グリッド上の列位置 (0-indexed)
  pchtype: PatchType; // パッチタイプ
  merged: {
    reg: number;      // レジスタマージ状態
    mem: number;      // メモリマージ状態
  };
  facebd: FaceBoundary;    // 面境界条件
  cornerbd: CornerBoundary; // 角境界条件
}
```

### 4.2 PatchType（パッチタイプ）

```typescript
type PatchType = 
  | "zt"   // Z-type top
  | "zb"   // Z-type bottom
  | "mt"   // M-type top
  | "mb"   // M-type bottom
  | "m"    // M-type (middle)
  | "x"    // X-type
  | "awe"  // Ancilla west-east
  | "i";   // Idle (未使用)
```

### 4.3 FaceBoundary（面境界条件）

パッチの4辺の境界条件。

```typescript
interface FaceBoundary {
  w: BoundaryType;  // West (西)
  n: BoundaryType;  // North (北)
  e: BoundaryType;  // East (東)
  s: BoundaryType;  // South (南)
}

type BoundaryType =
  | "i"   // Idle (アイドル/未接続)
  | "x"   // X境界
  | "z"   // Z境界
  | "pp"  // Pauli Product (パウリ積)
  | "lp"; // Logical Pauli
```

### 4.4 CornerBoundary（角境界条件）

パッチの4隅の境界条件。

```typescript
interface CornerBoundary {
  nw: CornerType;  // North-West (北西)
  ne: CornerType;  // North-East (北東)
  sw: CornerType;  // South-West (南西)
  se: CornerType;  // South-East (南東)
}

type CornerType =
  | "i"   // Idle
  | "c"   // Corner
  | "ie"  // Idle-Extended
  | "z";  // Z-type corner
```

---

## 5. events（イベント）★最重要★

時系列でのパッチ状態変化。**フロントエンドのアニメーション/タイムライン表示に使用**。

```typescript
interface PatchEvent {
  seq: number;           // イベント連番 (0から開始)
  cycle: number;         // 発生サイクル番号
  qisa_idx: number;      // 対応するQISA命令のインデックス
  inst: string;          // QISA命令名
  patch_delta: Patch[];  // 変化したパッチのリスト（変化後の状態）
}
```

### イベント例

```json
{
  "seq": 0,
  "cycle": 18,
  "qisa_idx": 3,
  "inst": "MERGE_INFO",
  "patch_delta": [
    {
      "pchidx": 0,
      "row": 0,
      "col": 0,
      "pchtype": "zt",
      "merged": { "reg": 0, "mem": 0 },
      "facebd": { "w": "x", "n": "x", "e": "z", "s": "pp" },
      "cornerbd": { "nw": "c", "ne": "i", "sw": "i", "se": "i" }
    },
    // ... 他の変化したパッチ
  ]
}
```

### 主要なQISA命令（inst）

| 命令 | 説明 |
|------|------|
| `PREP_INFO` | パッチ準備 |
| `LQI` | 論理量子ビット初期化 |
| `RUN_ESM` | エラーシンドローム測定実行 |
| `MERGE_INFO` | パッチマージ（CNOTの実装） |
| `SPLIT_INFO` | パッチ分割 |
| `INIT_INTMD` | 中間状態初期化 |
| `MEAS_INTMD` | 中間状態測定 |
| `PPM_INTERPRET` | パウリ積測定解釈 |
| `LQM_X` | X基底論理測定 |
| `LQM_Z` | Z基底論理測定 |

---

## 6. フロントエンド実装ガイド

### 6.1 グリッド描画

```javascript
// パッチグリッドの描画
const { rows, cols } = response.result.meta.patch_grid;

for (let row = 0; row < rows; row++) {
  for (let col = 0; col < cols; col++) {
    const patch = response.result.patch.initial.find(
      p => p.row === row && p.col === col
    );
    drawPatch(patch);
  }
}
```

### 6.2 タイムライン再生

```javascript
// イベントの時系列再生
const events = response.result.patch.events;
let currentState = [...response.result.patch.initial];

function applyEvent(event) {
  for (const delta of event.patch_delta) {
    const idx = currentState.findIndex(p => p.pchidx === delta.pchidx);
    if (idx !== -1) {
      currentState[idx] = delta;
    }
  }
  redrawGrid(currentState);
}

// アニメーション
let eventIndex = 0;
function animate() {
  if (eventIndex < events.length) {
    applyEvent(events[eventIndex]);
    eventIndex++;
    setTimeout(animate, 1000); // 1秒間隔
  }
}
```

### 6.3 境界条件の可視化

```javascript
// 境界タイプに応じた色分け
const boundaryColors = {
  "i": "transparent",  // アイドル
  "x": "#FF6B6B",      // X境界（赤系）
  "z": "#4ECDC4",      // Z境界（青緑系）
  "pp": "#FFE66D",     // パウリ積（黄色）
  "lp": "#95E1D3"      // 論理パウリ（緑系）
};
```

---

## 7. サンプルレスポンス

### Bell状態 (H + CNOT)

- **入力量子ビット**: 2
- **総サイクル**: 17,672
- **イベント数**: 2
  1. `MERGE_INFO` @ cycle 18 - CNOTのためのパッチマージ
  2. `SPLIT_INFO` @ cycle 5,121 - CNOT後のパッチ分割

### GHZ状態 (H + CNOT + CNOT)

- **入力量子ビット**: 3
- **総サイクル**: 29,014
- **イベント数**: 5
  1. `MERGE_INFO` @ cycle 18
  2. `SPLIT_INFO` @ cycle 5,125
  3. `PREP_INFO` @ cycle 10,750
  4. `MERGE_INFO` @ cycle 10,752
  5. `SPLIT_INFO` @ cycle 16,463

---

## 8. 制限事項

1. **CNOTが必須**: 単一量子ビット操作のみの回路はサポートされません
2. **最小3量子ビット**: 2量子ビット以下は自動パディング
3. **実行時間**: 1回路あたり5〜15分程度かかります

---

## 9. エラーレスポンス

```json
{
  "detail": "XQsim simulation error: sys.exit() was called..."
}
```

| HTTPステータス | 説明 |
|---------------|------|
| 400 | 無効なQASMまたは非対応の回路 |
| 429 | 他のトレースが実行中 |
| 504 | タイムアウト |

---

## 10. TypeScript型定義

完全な型定義は以下のファイルを参照してください：

```typescript
// types/xqsim.d.ts として保存推奨

export interface TraceResponse {
  result: {
    meta: Meta;
    input: Input;
    compiled: Compiled;
    patch: {
      initial: Patch[];
      events: PatchEvent[];
    };
  };
}

export interface Meta {
  version: number;
  config: string;
  block_type: string;
  code_distance: number;
  patch_grid: { rows: number; cols: number };
  num_patches: number;
  total_cycles: number;
  elapsed_seconds: number;
  termination_reason: "normal" | "timeout" | "max_cycles";
  forced_terminations: string[];
  stability_check_failures: string[];
  warnings: string[];
}

export interface Input {
  qasm: string;
  num_qasm_qubits: number;
  num_compile_qubits: number;
  padding_applied: boolean;
}

export interface Compiled {
  clifford_t_qasm: string;
  clifford_t_qasm_padded: string | null;
  qisa: string[];
  qbin_name: string;
}

export interface Patch {
  pchidx: number;
  row: number;
  col: number;
  pchtype: "zt" | "zb" | "mt" | "mb" | "m" | "x" | "awe" | "i";
  merged: { reg: number; mem: number };
  facebd: { w: string; n: string; e: string; s: string };
  cornerbd: { nw: string; ne: string; sw: string; se: string };
}

export interface PatchEvent {
  seq: number;
  cycle: number;
  qisa_idx: number;
  inst: string;
  patch_delta: Patch[];
}
```

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 3 | 2024-12 | 初版作成 |

