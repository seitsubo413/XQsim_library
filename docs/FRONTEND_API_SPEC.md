# XQsim バックエンドAPI仕様書（フロントエンド開発用）

**バージョン:** 0.3.0  
**更新日:** 2025年1月6日

---

## 概要

このAPIはOpenQASM 2.0形式の量子回路を入力として受け取り、XQsimシミュレータを実行して**パッチ情報の時系列データ**をJSON形式で返します。

```
[QASM入力] → [コンパイル] → [シミュレーション] → [パッチ情報JSON]
```

---

## 1. エンドポイント一覧

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/health` | ヘルスチェック・状態確認 |
| POST | `/trace` | パッチトレース生成（メイン機能） |

---

## 2. ヘルスチェック

### GET `/health`

サーバー状態と現在の制限値を返します。

#### レスポンス例

```json
{
  "status": "ok",
  "trace_in_progress": false,
  "limits": {
    "max_qasm_size_bytes": 1048576,
    "max_qubits": 20,
    "max_depth": 1000,
    "max_instructions": 10000,
    "trace_timeout_seconds": 86400
  }
}
```

| フィールド | 型 | 説明 |
|------------|-----|------|
| `status` | string | `"ok"` = 正常 |
| `trace_in_progress` | boolean | 現在シミュレーション実行中かどうか |
| `limits` | object | 入力制限値 |

---

## 3. パッチトレース生成

### POST `/trace`

QASMからパッチの時系列情報を生成します。

> ⚠️ **注意**: 処理に数分〜十数分かかります。同時実行は不可（429エラー）。

#### リクエスト

```json
{
  "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\ncx q[0],q[1];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];",
  "config": "example_cmos_d5",
  "keep_artifacts": false,
  "debug_logging": false
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|------------|------|
| `qasm` | string | ✅ | - | OpenQASM 2.0形式の量子回路 |
| `config` | string | ❌ | `"example_cmos_d5"` | 設定名（`src/configs/*.json`） |
| `keep_artifacts` | boolean | ❌ | `false` | デバッグ用中間ファイル保持 |
| `debug_logging` | boolean | ❌ | `false` | 詳細ログ出力 |

#### 成功レスポンス (200 OK)

```json
{
  "result": {
    "meta": { ... },
    "input": { ... },
    "compiled": { ... },
    "patch": { ... }
  }
}
```

---

## 4. レスポンス構造の詳細

### 4.1 `result.meta` - メタ情報

シミュレーション全体の情報。

```json
{
  "meta": {
    "version": 3,
    "config": "example_cmos_d5",
    "block_type": "Distillation",
    "code_distance": 5,
    "patch_grid": {
      "rows": 3,
      "cols": 4
    },
    "num_patches": 12,
    "total_cycles": 17672,
    "elapsed_seconds": 600.56,
    "termination_reason": "normal",
    "forced_terminations": [],
    "stability_check_failures": [],
    "warnings": [
      "Padding applied: original 2 qubits -> 3 qubits for compilation. The last qubit (index 2) is unused."
    ]
  }
}
```

| フィールド | 型 | 説明 |
|------------|-----|------|
| `version` | number | API出力バージョン |
| `config` | string | 使用した設定名 |
| `block_type` | string | ブロックタイプ（通常 `"Distillation"`） |
| `code_distance` | number | 誤り訂正符号の距離 |
| `patch_grid.rows` | number | パッチグリッドの行数 |
| `patch_grid.cols` | number | パッチグリッドの列数 |
| `num_patches` | number | 総パッチ数（`rows × cols`） |
| `total_cycles` | number | シミュレーション総サイクル数 |
| `elapsed_seconds` | number | 実行時間（秒） |
| `termination_reason` | string | 終了理由（`"normal"` / `"timeout"` / `"error"`） |
| `warnings` | string[] | 警告メッセージ |

---

### 4.2 `result.input` - 入力情報

入力されたQASMの情報。

```json
{
  "input": {
    "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\n...",
    "num_qasm_qubits": 2,
    "num_compile_qubits": 3,
    "padding_applied": true
  }
}
```

| フィールド | 型 | 説明 |
|------------|-----|------|
| `qasm` | string | 元のQASM文字列 |
| `num_qasm_qubits` | number | 元の量子ビット数 |
| `num_compile_qubits` | number | コンパイル時の量子ビット数（パディング後） |
| `padding_applied` | boolean | パディングが適用されたか |

> ℹ️ XQsimの制約により、量子ビット数は奇数または2に調整されます。

---

### 4.3 `result.compiled` - コンパイル結果

量子コンパイラの出力。

```json
{
  "compiled": {
    "clifford_t_qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\n...",
    "clifford_t_qasm_padded": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\n...",
    "qisa": [
      "PREP_INFO     NA   NA    NA   NA",
      "LQI           NA   NA    0x00 [-,-,T,T,T,-,-,-,-,-,-,-,-,-,-,-,]",
      "RUN_ESM       NA   NA    NA   NA",
      "MERGE_INFO    NA   NA    0x00 [I,I,Z,Z,I,I,I,I,I,I,I,I,I,I,I,I,]",
      ...
    ],
    "qbin_name": "api_253b349e8e7e4caaa9b8e2a79d66a723_n3"
  }
}
```

| フィールド | 型 | 説明 |
|------------|-----|------|
| `clifford_t_qasm` | string | Clifford+T分解後のQASM |
| `clifford_t_qasm_padded` | string | パディング後のQASM |
| `qisa` | string[] | QISA命令列（表面符号用アセンブリ） |
| `qbin_name` | string | 生成されたバイナリ名 |

---

### 4.4 `result.patch` - パッチ情報（⭐ メイン出力）

パッチの初期状態とイベント履歴。**フロントエンドで可視化する主要データ**。

```json
{
  "patch": {
    "initial": [ ... ],   // 初期状態のパッチ配列
    "events": [ ... ]     // 状態変化イベント配列
  }
}
```

---

### 4.4.1 `patch.initial` - 初期パッチ状態

シミュレーション開始時の全パッチの状態。

```json
{
  "initial": [
    {
      "pchidx": 0,
      "row": 0,
      "col": 0,
      "pchtype": "zt",
      "merged": {
        "reg": 0,
        "mem": 0
      },
      "facebd": {
        "w": "i",
        "n": "i",
        "e": "i",
        "s": "i"
      },
      "cornerbd": {
        "nw": "i",
        "ne": "i",
        "sw": "i",
        "se": "i"
      }
    },
    ...
  ]
}
```

#### パッチオブジェクトの構造

| フィールド | 型 | 説明 |
|------------|-----|------|
| `pchidx` | number | パッチインデックス（0から連番） |
| `row` | number | グリッド上の行位置（0始まり） |
| `col` | number | グリッド上の列位置（0始まり） |
| `pchtype` | string | パッチタイプ（下表参照） |
| `merged.reg` | number | マージされたレジスタID |
| `merged.mem` | number | マージされたメモリID |
| `facebd` | object | 4辺の境界条件（w/n/e/s） |
| `cornerbd` | object | 4角の境界条件（nw/ne/sw/se） |

#### パッチタイプ（`pchtype`）

| 値 | 説明 | 可視化での推奨色 |
|-----|------|------------------|
| `"zt"` | Z-type top | 青系 |
| `"zb"` | Z-type bottom | 青系（暗め） |
| `"mt"` | Merge top | 緑系 |
| `"mb"` | Merge bottom | 緑系（暗め） |
| `"m"` | Merge | 緑系 |
| `"x"` | X-type | 赤系 |
| `"awe"` | Ancilla west-east | 黄系 |
| `"i"` | Idle（未使用） | グレー |

#### 境界条件（`facebd` / `cornerbd`）

| 値 | 説明 | 可視化での推奨表現 |
|-----|------|---------------------|
| `"i"` | Idle（境界なし） | 点線 or 非表示 |
| `"x"` | X境界 | 赤線 |
| `"z"` | Z境界 | 青線 |
| `"pp"` | Pauli product | 紫線 |
| `"c"` | Corner | 黒点 |
| `"ze"` | Z endpoint | 青マーカー |

---

### 4.4.2 `patch.events` - 状態変化イベント

パッチ状態が変化したタイミングと内容。

```json
{
  "events": [
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
        ...
      ]
    },
    ...
  ]
}
```

| フィールド | 型 | 説明 |
|------------|-----|------|
| `seq` | number | イベント連番（0始まり） |
| `cycle` | number | 発生サイクル番号 |
| `qisa_idx` | number | 対応するQISA命令インデックス |
| `inst` | string | 命令名（`MERGE_INFO`, `SPLIT_INFO`など） |
| `patch_delta` | array | 変化したパッチの新状態（差分） |

> 💡 `patch_delta`には変化したパッチのみが含まれます。変化していないパッチは省略されます。

---

## 5. エラーレスポンス

| HTTPステータス | 意味 | 対応方法 |
|----------------|------|----------|
| 400 | 不正な入力・シミュレーションエラー | QASM構文やパラメータを確認 |
| 429 | 既にシミュレーション実行中 | しばらく待ってリトライ |
| 500 | 内部エラー | サーバーログを確認 |
| 504 | タイムアウト | 回路を簡素化して再試行 |

```json
{
  "detail": "Error message here"
}
```

---

## 6. TypeScript型定義

フロントエンド開発用の型定義：

```typescript
// ============================================================================
// API Types
// ============================================================================

interface HealthResponse {
  status: "ok";
  trace_in_progress: boolean;
  limits: {
    max_qasm_size_bytes: number;
    max_qubits: number;
    max_depth: number;
    max_instructions: number;
    trace_timeout_seconds: number;
  };
}

interface TraceRequest {
  qasm: string;
  config?: string;
  keep_artifacts?: boolean;
  debug_logging?: boolean;
}

interface TraceResponse {
  result: TraceResult;
}

// ============================================================================
// Result Structure
// ============================================================================

interface TraceResult {
  meta: MetaInfo;
  input: InputInfo;
  compiled: CompiledInfo;
  patch: PatchInfo;
}

interface MetaInfo {
  version: number;
  config: string;
  block_type: string;
  code_distance: number;
  patch_grid: {
    rows: number;
    cols: number;
  };
  num_patches: number;
  total_cycles: number;
  elapsed_seconds: number;
  termination_reason: "normal" | "timeout" | "error";
  forced_terminations: string[];
  stability_check_failures: string[];
  warnings: string[];
}

interface InputInfo {
  qasm: string;
  num_qasm_qubits: number;
  num_compile_qubits: number;
  padding_applied: boolean;
}

interface CompiledInfo {
  clifford_t_qasm: string;
  clifford_t_qasm_padded: string;
  qisa: string[];
  qbin_name: string;
}

// ============================================================================
// Patch Types (⭐ 可視化で使用)
// ============================================================================

interface PatchInfo {
  initial: Patch[];
  events: PatchEvent[];
}

type PatchType = "zt" | "zb" | "mt" | "mb" | "m" | "x" | "awe" | "i";
type BoundaryType = "i" | "x" | "z" | "pp" | "c" | "ze";

interface Patch {
  pchidx: number;
  row: number;
  col: number;
  pchtype: PatchType;
  merged: {
    reg: number;
    mem: number;
  };
  facebd: {
    w: BoundaryType;
    n: BoundaryType;
    e: BoundaryType;
    s: BoundaryType;
  };
  cornerbd: {
    nw: BoundaryType;
    ne: BoundaryType;
    sw: BoundaryType;
    se: BoundaryType;
  };
}

interface PatchEvent {
  seq: number;
  cycle: number;
  qisa_idx: number;
  inst: string;
  patch_delta: Patch[];
}
```

---

## 7. 可視化のヒント

### 7.1 グリッド描画

```
rows=3, cols=4 の場合:

     col 0    col 1    col 2    col 3
    ┌────────┬────────┬────────┬────────┐
row 0 │ pch 0  │ pch 1  │ pch 2  │ pch 3  │
    ├────────┼────────┼────────┼────────┤
row 1 │ pch 4  │ pch 5  │ pch 6  │ pch 7  │
    ├────────┼────────┼────────┼────────┤
row 2 │ pch 8  │ pch 9  │ pch 10 │ pch 11 │
    └────────┴────────┴────────┴────────┘
```

### 7.2 タイムライン表示

```
cycle 0    → initial state
cycle 18   → events[0] (MERGE_INFO)  → patch_deltaを適用
cycle 5121 → events[1] (SPLIT_INFO)  → patch_deltaを適用
...
cycle 17672 → end
```

### 7.3 状態管理ロジック（擬似コード）

```typescript
function getPatchStateAtCycle(result: TraceResult, targetCycle: number): Patch[] {
  // 初期状態をコピー
  const patches = structuredClone(result.patch.initial);
  
  // targetCycle以下のイベントを順に適用
  for (const event of result.patch.events) {
    if (event.cycle > targetCycle) break;
    
    for (const delta of event.patch_delta) {
      const idx = patches.findIndex(p => p.pchidx === delta.pchidx);
      if (idx !== -1) {
        patches[idx] = delta;
      }
    }
  }
  
  return patches;
}
```

---

## 8. サンプルリクエスト

### cURL

```bash
# ヘルスチェック
curl http://localhost:8000/health

# パッチトレース（2量子ビットCNOT）
curl -X POST http://localhost:8000/trace \
  -H "Content-Type: application/json" \
  -d '{
    "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\ncx q[0],q[1];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];"
  }'
```

### JavaScript/TypeScript

```typescript
async function tracePatches(qasm: string): Promise<TraceResult> {
  const response = await fetch("http://localhost:8000/trace", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ qasm }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  const data: TraceResponse = await response.json();
  return data.result;
}
```

---

## 9. 制限事項

| 項目 | 制限値 | 備考 |
|------|--------|------|
| QASM最大サイズ | 1MB | UTF-8バイト数 |
| 最大量子ビット数 | 20 | |
| 最大回路深さ | 1000 | |
| 最大命令数 | 10000 | |
| タイムアウト | 24時間 | 環境変数で調整可能 |
| 同時実行 | 1リクエスト | 直列実行のみ |

---

## 10. 実行時間の目安

| 量子ビット数 | ゲート数 | 実行時間 |
|--------------|----------|----------|
| 2 | 1 CNOT | 約8〜10分 |
| 3 | 2 CNOT | 約15分 |

> ⚠️ フロントエンドではローディング表示と進捗確認を実装することを推奨。

---

## 付録: 出力JSONの完全例

`test_results_v2/test_cnot_simple.json` を参照してください。

