/**
 * XQsim Patch Trace API - TypeScript型定義
 * @version 3
 */

// ========================================
// メインレスポンス
// ========================================

export interface TraceResponse {
  result: TraceResult;
}

export interface TraceResult {
  meta: Meta;
  input: Input;
  compiled: Compiled;
  patch: PatchData;
}

// ========================================
// メタデータ
// ========================================

export interface Meta {
  /** APIバージョン (現在: 3) */
  version: number;
  /** 使用した設定名 */
  config: string;
  /** ブロックタイプ */
  block_type: string;
  /** 表面符号の距離 */
  code_distance: number;
  /** パッチグリッドのサイズ */
  patch_grid: PatchGrid;
  /** 総パッチ数 */
  num_patches: number;
  /** シミュレーション総サイクル数 */
  total_cycles: number;
  /** 実行時間（秒） */
  elapsed_seconds: number;
  /** 終了理由 */
  termination_reason: TerminationReason;
  /** 強制終了の記録 */
  forced_terminations: string[];
  /** 安定性チェック失敗の記録 */
  stability_check_failures: string[];
  /** 警告メッセージ */
  warnings: string[];
}

export interface PatchGrid {
  rows: number;
  cols: number;
}

export type TerminationReason = "normal" | "timeout" | "max_cycles";

// ========================================
// 入力情報
// ========================================

export interface Input {
  /** 入力QASM（元のまま） */
  qasm: string;
  /** 元のQASMの量子ビット数 */
  num_qasm_qubits: number;
  /** コンパイル時の量子ビット数 */
  num_compile_qubits: number;
  /** パディングが適用されたか */
  padding_applied: boolean;
}

// ========================================
// コンパイル結果
// ========================================

export interface Compiled {
  /** Clifford+Tゲートに変換されたQASM */
  clifford_t_qasm: string;
  /** パディング適用後のQASM（適用時のみ） */
  clifford_t_qasm_padded: string | null;
  /** QISA命令リスト */
  qisa: string[];
  /** 生成されたバイナリ名 */
  qbin_name: string;
}

// ========================================
// パッチデータ
// ========================================

export interface PatchData {
  /** 初期状態の全パッチ */
  initial: Patch[];
  /** 時系列イベント */
  events: PatchEvent[];
}

// ========================================
// パッチ
// ========================================

export interface Patch {
  /** パッチインデックス (0〜num_patches-1) */
  pchidx: number;
  /** グリッド上の行位置 (0-indexed) */
  row: number;
  /** グリッド上の列位置 (0-indexed) */
  col: number;
  /** パッチタイプ */
  pchtype: PatchType;
  /** マージ状態 */
  merged: MergeState;
  /** 面境界条件 */
  facebd: FaceBoundary;
  /** 角境界条件 */
  cornerbd: CornerBoundary;
}

/**
 * パッチタイプ
 * - zt: Z-type top
 * - zb: Z-type bottom
 * - mt: M-type top
 * - mb: M-type bottom
 * - m: M-type (middle)
 * - x: X-type
 * - awe: Ancilla west-east
 * - i: Idle (未使用)
 */
export type PatchType = "zt" | "zb" | "mt" | "mb" | "m" | "x" | "awe" | "i";

export interface MergeState {
  /** レジスタマージ状態 */
  reg: number;
  /** メモリマージ状態 */
  mem: number;
}

// ========================================
// 境界条件
// ========================================

export interface FaceBoundary {
  /** West (西) */
  w: BoundaryType;
  /** North (北) */
  n: BoundaryType;
  /** East (東) */
  e: BoundaryType;
  /** South (南) */
  s: BoundaryType;
}

/**
 * 境界タイプ
 * - i: Idle (アイドル/未接続)
 * - x: X境界
 * - z: Z境界
 * - pp: Pauli Product (パウリ積)
 * - lp: Logical Pauli
 */
export type BoundaryType = "i" | "x" | "z" | "pp" | "lp";

export interface CornerBoundary {
  /** North-West (北西) */
  nw: CornerType;
  /** North-East (北東) */
  ne: CornerType;
  /** South-West (南西) */
  sw: CornerType;
  /** South-East (南東) */
  se: CornerType;
}

/**
 * 角タイプ
 * - i: Idle
 * - c: Corner
 * - ie: Idle-Extended
 * - z: Z-type corner
 */
export type CornerType = "i" | "c" | "ie" | "z";

// ========================================
// イベント
// ========================================

export interface PatchEvent {
  /** イベント連番 (0から開始) */
  seq: number;
  /** 発生サイクル番号 */
  cycle: number;
  /** 対応するQISA命令のインデックス */
  qisa_idx: number;
  /** QISA命令名 */
  inst: QISAInstruction;
  /** 変化したパッチのリスト（変化後の状態） */
  patch_delta: Patch[];
}

/**
 * QISA命令
 */
export type QISAInstruction =
  | "PREP_INFO"      // パッチ準備
  | "LQI"            // 論理量子ビット初期化
  | "RUN_ESM"        // エラーシンドローム測定実行
  | "MERGE_INFO"     // パッチマージ（CNOTの実装）
  | "SPLIT_INFO"     // パッチ分割
  | "INIT_INTMD"     // 中間状態初期化
  | "MEAS_INTMD"     // 中間状態測定
  | "PPM_INTERPRET"  // パウリ積測定解釈
  | "LQM_X"          // X基底論理測定
  | "LQM_Z"          // Z基底論理測定
  | string;          // その他の命令

// ========================================
// ヘルパー関数型
// ========================================

/**
 * パッチをグリッド位置で検索
 */
export type FindPatchByPosition = (
  patches: Patch[],
  row: number,
  col: number
) => Patch | undefined;

/**
 * イベントを適用して新しい状態を取得
 */
export type ApplyPatchEvent = (
  currentState: Patch[],
  event: PatchEvent
) => Patch[];

// ========================================
// リクエスト型
// ========================================

export interface TraceRequest {
  /** OpenQASM 2.0形式の量子回路 */
  qasm: string;
  /** 設定名 (デフォルト: "example_cmos_d5") */
  config?: string;
  /** アーティファクトを保持するか */
  keep_artifacts?: boolean;
}

// ========================================
// エラーレスポンス
// ========================================

export interface ErrorResponse {
  detail: string;
}

// ========================================
// ヘルスチェック
// ========================================

export interface HealthResponse {
  status: "ok" | "error";
  version: string;
  ray_initialized: boolean;
  trace_in_progress: boolean;
  limits: {
    max_qasm_size_bytes: number;
    max_qubits: number;
    max_depth: number;
    max_instructions: number;
    timeout_seconds: number;
    max_cycles: number;
  };
}

