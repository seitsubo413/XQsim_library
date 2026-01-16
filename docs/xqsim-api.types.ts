/**
 * XQsim Patch Trace API TypeScript型定義
 * 
 * 使用方法:
 * このファイルをフロントエンドプロジェクトにコピーして使用してください。
 * 
 * @version 0.4.0
 * @date 2026-01-14
 */

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * GET /health レスポンス
 */
export interface HealthResponse {
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

/**
 * POST /trace リクエスト
 */
export interface TraceRequest {
  /** OpenQASM 2.0形式の量子回路 (必須) */
  qasm: string;
  /** 設定名 (デフォルト: "example_cmos_d5") */
  config?: string;
  /** デバッグ用中間ファイル保持 (デフォルト: false) */
  keep_artifacts?: boolean;
  /** 詳細ログ出力 (デフォルト: false) */
  debug_logging?: boolean;
}

/**
 * POST /trace 成功レスポンス
 */
export interface TraceResponse {
  result: TraceResult;
}

/**
 * エラーレスポンス
 */
export interface ErrorResponse {
  detail: string;
}

// ============================================================================
// Result Structure
// ============================================================================

/**
 * トレース結果のメイン構造
 */
export interface TraceResult {
  /** シミュレーションのメタ情報 */
  meta: MetaInfo;
  /** 入力されたQASMの情報 */
  input: InputInfo;
  /** コンパイル結果 */
  compiled: CompiledInfo;
  /** パッチ情報 (⭐ 可視化で使用するメインデータ) */
  patch: PatchInfo;
  /** 論理キュービットマッピング */
  logical_qubit_mapping: LogicalQubitMapping[];
  /** Clifford+T回路実行追跡 (⭐ 新機能) */
  clifford_t_execution_trace: CliffordTExecutionTrace;
}

/**
 * メタ情報
 */
export interface MetaInfo {
  /** API出力バージョン */
  version: number;
  /** 使用した設定名 */
  config: string;
  /** ブロックタイプ (通常 "Distillation") */
  block_type: string;
  /** 誤り訂正符号の距離 */
  code_distance: number;
  /** パッチグリッドのサイズ */
  patch_grid: {
    rows: number;
    cols: number;
  };
  /** 総パッチ数 (rows × cols) */
  num_patches: number;
  /** シミュレーション総サイクル数 */
  total_cycles: number;
  /** 実行時間（秒） */
  elapsed_seconds: number;
  /** 終了理由 */
  termination_reason: "normal" | "timeout" | "error";
  /** 強制終了メッセージ */
  forced_terminations: string[];
  /** 安定性チェック失敗メッセージ */
  stability_check_failures: string[];
  /** 警告メッセージ */
  warnings: string[];
}

/**
 * 入力情報
 */
export interface InputInfo {
  /** 元のQASM文字列 */
  qasm: string;
  /** 元の量子ビット数 */
  num_qasm_qubits: number;
  /** コンパイル時の量子ビット数（パディング後） */
  num_compile_qubits: number;
  /** パディングが適用されたか */
  padding_applied: boolean;
}

/**
 * コンパイル結果
 */
export interface CompiledInfo {
  /** Clifford+T分解後のQASM */
  clifford_t_qasm: string;
  /** パディング後のQASM */
  clifford_t_qasm_padded: string;
  /** QISA命令列（表面符号用アセンブリ） */
  qisa: string[];
  /** 生成されたバイナリ名 */
  qbin_name: string;
}

// ============================================================================
// Patch Types (⭐ 可視化で使用するメインデータ)
// ============================================================================

/**
 * パッチ情報
 */
export interface PatchInfo {
  /** 初期状態のパッチ配列 */
  initial: Patch[];
  /** 状態変化イベント配列 */
  events: PatchEvent[];
}

/**
 * パッチタイプ
 * 
 * | 値    | 説明             | 推奨色     |
 * |-------|------------------|------------|
 * | "zt"  | Z-type top       | 青系       |
 * | "zb"  | Z-type bottom    | 青系（暗め）|
 * | "mt"  | Merge top        | 緑系       |
 * | "mb"  | Merge bottom     | 緑系（暗め）|
 * | "m"   | Merge            | 緑系       |
 * | "x"   | X-type           | 赤系       |
 * | "awe" | Ancilla west-east| 黄系       |
 * | "i"   | Idle（未使用）    | グレー     |
 */
export type PatchType = "zt" | "zb" | "mt" | "mb" | "m" | "x" | "awe" | "i";

/**
 * 境界条件タイプ
 * 
 * | 値   | 説明           | 推奨表現    |
 * |------|----------------|-------------|
 * | "i"  | Idle（境界なし）| 点線 or 非表示 |
 * | "x"  | X境界          | 赤線        |
 * | "z"  | Z境界          | 青線        |
 * | "pp" | Pauli product  | 紫線        |
 * | "c"  | Corner         | 黒点        |
 * | "ze" | Z endpoint     | 青マーカー  |
 */
export type BoundaryType = "i" | "x" | "z" | "pp" | "c" | "ze";

/**
 * パッチオブジェクト
 */
export interface Patch {
  /** パッチインデックス（0から連番） */
  pchidx: number;
  /** グリッド上の行位置（0始まり） */
  row: number;
  /** グリッド上の列位置（0始まり） */
  col: number;
  /** パッチタイプ */
  pchtype: PatchType;
  /** マージ情報 */
  merged: {
    /** マージされたレジスタID */
    reg: number;
    /** マージされたメモリID */
    mem: number;
  };
  /** 4辺の境界条件 */
  facebd: {
    /** 西（左） */
    w: BoundaryType;
    /** 北（上） */
    n: BoundaryType;
    /** 東（右） */
    e: BoundaryType;
    /** 南（下） */
    s: BoundaryType;
  };
  /** 4角の境界条件 */
  cornerbd: {
    /** 北西（左上） */
    nw: BoundaryType;
    /** 北東（右上） */
    ne: BoundaryType;
    /** 南西（左下） */
    sw: BoundaryType;
    /** 南東（右下） */
    se: BoundaryType;
  };
}

/**
 * パッチ状態変化イベント
 */
export interface PatchEvent {
  /** イベント連番（0始まり） */
  seq: number;
  /** 発生サイクル番号 */
  cycle: number;
  /** 対応するQISA命令インデックス */
  qisa_idx: number;
  /** 命令名 (例: "MERGE_INFO", "SPLIT_INFO") */
  inst: string;
  /** 変化したパッチの新状態（差分のみ） */
  patch_delta: Patch[];
}

// ============================================================================
// Logical Qubit Mapping Types
// ============================================================================

/**
 * 論理キュービットの役割
 */
export type LogicalQubitRole = "z_ancilla" | "m_ancilla" | "data" | "padding";

/**
 * 論理キュービットマッピング
 */
export interface LogicalQubitMapping {
  /** 論理キュービットインデックス */
  lq_idx: number;
  /** 役割 */
  role: LogicalQubitRole;
  /** QASMのキュービットインデックス（role="data"の場合のみ） */
  qubit_index?: number;
  /** 説明 */
  description: string;
  /** 対応するパッチのインデックス */
  patch_indices: number[];
  /** パッチのグリッド座標 [row, col] */
  patch_coords: [number, number][];
  /** パッチタイプ */
  pchtype: PatchType;
}

// ============================================================================
// Clifford+T Execution Trace Types (⭐ 新機能)
// ============================================================================

/**
 * ゲートの実行タイプ
 */
export type GateExecutionType = "ppr" | "ppm" | "sqm" | "pauli_frame" | "no_effect";

/**
 * パウリ吸収効果
 */
export type AbsorptionEffect = "transform_pauli" | "propagate_pauli";

/**
 * パウリ吸収情報
 */
export interface AbsorptionInfo {
  /** 効果の種類 */
  effect: AbsorptionEffect;
  /** 変換前のパウリ（transform_pauliの場合） */
  pauli_before?: string;
  /** 変換後のパウリ（transform_pauliの場合） */
  pauli_after?: string;
  /** 対象キュービット（transform_pauliの場合） */
  qubit?: number[];
  /** パウリ伝播元（propagate_pauliの場合） */
  source_qubit?: number[];
  /** パウリ伝播先（propagate_pauliの場合） */
  target_qubit?: number[];
  /** 追加されたパウリ（propagate_pauliの場合） */
  added_pauli?: string;
}

/**
 * ゲート追跡エントリ
 */
export interface GateTraceEntry {
  /** ゲートインデックス（Clifford+T回路内での位置） */
  gate_idx: number;
  /** ゲート名（小文字: h, cx, s, t, measure） */
  gate: string;
  /** ゲートが作用するキュービット */
  qubits: number[][];
  /** 実行タイプ */
  execution_type: GateExecutionType;
  
  // PPR/PPMの場合
  /** パウリ積 */
  pauli_product?: string[];
  /** パウリ積が作用するキュービット */
  target_qubits?: number[][];
  /** MERGE操作のサイクル */
  cycle_start?: number;
  /** SPLIT操作のサイクル */
  cycle_end?: number;
  
  // SQMの場合
  /** 測定基底 */
  basis?: "X" | "Z";
  /** このサイクル以降に実行 */
  cycle_after?: number;
  /** このサイクル以前に完了 */
  cycle_before?: number;
  
  // Pauli Frameの場合
  /** 吸収先の情報 */
  absorbed_into?: AbsorptionInfo[];
}

/**
 * Clifford+T実行追跡のサマリー
 */
export interface CliffordTExecutionSummary {
  /** 総ゲート数 */
  total_gates: number;
  /** PPR操作数（Tゲート数） */
  ppr_count: number;
  /** PPM操作数（複数キュービット測定数） */
  ppm_count: number;
  /** SQM操作数（単一キュービット測定数） */
  sqm_count: number;
  /** Pauli Frameゲート数 */
  pauli_frame_count: number;
  /** すべてのゲートが追跡されたか */
  all_gates_traced: boolean;
}

/**
 * Clifford+T実行追跡
 */
export interface CliffordTExecutionTrace {
  /** ゲートごとの追跡情報 */
  gates: GateTraceEntry[];
  /** サマリー */
  summary: CliffordTExecutionSummary;
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * パッチタイプごとの推奨カラー
 */
export const PATCH_TYPE_COLORS: Record<PatchType, string> = {
  zt: "#3B82F6",   // blue-500
  zb: "#1E40AF",   // blue-800
  mt: "#22C55E",   // green-500
  mb: "#166534",   // green-800
  m: "#16A34A",    // green-600
  x: "#EF4444",    // red-500
  awe: "#EAB308",  // yellow-500
  i: "#9CA3AF",    // gray-400
};

/**
 * 境界条件ごとの推奨カラー
 */
export const BOUNDARY_TYPE_COLORS: Record<BoundaryType, string> = {
  i: "transparent",
  x: "#EF4444",    // red-500
  z: "#3B82F6",    // blue-500
  pp: "#A855F7",   // purple-500
  c: "#000000",    // black
  ze: "#1D4ED8",   // blue-700
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * 指定サイクル時点でのパッチ状態を取得
 * 
 * @param result トレース結果
 * @param targetCycle 取得したいサイクル番号
 * @returns そのサイクル時点でのパッチ配列
 */
export function getPatchStateAtCycle(result: TraceResult, targetCycle: number): Patch[] {
  // 初期状態をディープコピー
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

/**
 * パッチインデックスから行・列位置を取得
 * 
 * @param pchidx パッチインデックス
 * @param cols 列数
 * @returns { row, col }
 */
export function getPositionFromIndex(pchidx: number, cols: number): { row: number; col: number } {
  return {
    row: Math.floor(pchidx / cols),
    col: pchidx % cols,
  };
}

/**
 * 全イベントのサイクル番号リストを取得（タイムライン用）
 * 
 * @param result トレース結果
 * @returns サイクル番号の配列（0, イベントサイクル, 最終サイクル）
 */
export function getTimelinePoints(result: TraceResult): number[] {
  const points = [0];
  for (const event of result.patch.events) {
    points.push(event.cycle);
  }
  points.push(result.meta.total_cycles);
  return [...new Set(points)].sort((a, b) => a - b);
}

/**
 * QASMキュービットインデックスから対応するパッチを取得
 * 
 * @param result トレース結果
 * @param qasmQubitIndex QASMの量子ビットインデックス
 * @returns 対応する論理キュービットマッピング、見つからない場合はundefined
 */
export function getLogicalQubitForQasmQubit(
  result: TraceResult,
  qasmQubitIndex: number
): LogicalQubitMapping | undefined {
  return result.logical_qubit_mapping.find(
    (lq) => lq.role === "data" && lq.qubit_index === qasmQubitIndex
  );
}

/**
 * 指定サイクル時点でのゲート実行状態を取得
 * 
 * @param trace Clifford+T実行追跡
 * @param cycle 対象サイクル
 * @returns 実行中と完了済みのゲート
 */
export function getGateStateAtCycle(
  trace: CliffordTExecutionTrace,
  cycle: number
): { executing: GateTraceEntry[]; completed: GateTraceEntry[] } {
  const executing: GateTraceEntry[] = [];
  const completed: GateTraceEntry[] = [];

  for (const gate of trace.gates) {
    if (gate.execution_type === "ppr" || gate.execution_type === "ppm") {
      if (gate.cycle_start !== undefined && gate.cycle_end !== undefined) {
        if (cycle >= gate.cycle_start && cycle <= gate.cycle_end) {
          executing.push(gate);
        } else if (cycle > gate.cycle_end) {
          completed.push(gate);
        }
      }
    } else if (gate.execution_type === "sqm") {
      if (gate.cycle_after !== undefined && gate.cycle_before !== undefined) {
        if (cycle >= gate.cycle_after && cycle <= gate.cycle_before) {
          executing.push(gate);
        } else if (cycle > gate.cycle_before) {
          completed.push(gate);
        }
      }
    } else if (gate.execution_type === "pauli_frame") {
      // Pauli frameゲートは最初のPPM/PPRより前に完了
      completed.push(gate);
    }
  }

  return { executing, completed };
}

/**
 * ゲートの実行状態をわかりやすい文字列で取得
 * 
 * @param gate ゲート追跡エントリ
 * @returns 状態の説明文
 */
export function getGateStatusLabel(gate: GateTraceEntry): string {
  switch (gate.execution_type) {
    case "ppr":
      return `PPR (T gate) @ cycle ${gate.cycle_start}-${gate.cycle_end}`;
    case "ppm":
      return `PPM (Measure) @ cycle ${gate.cycle_start}-${gate.cycle_end}`;
    case "sqm":
      return `SQM (${gate.basis} basis) @ cycle ${gate.cycle_after}-${gate.cycle_before}`;
    case "pauli_frame":
      return "Pauli Frame (absorbed)";
    default:
      return "No effect";
  }
}

