# XQsim: Cross-technology Quantum control processor SIMulator

XQsim is a simulation framework for quantum control processors supporting fault-tolerant quantum computing (FTQC).

This repository provides an **API server** that takes OpenQASM 2.0 quantum circuits as input and returns patch trace information (time-series JSON) from the XQsim simulator.

## Quick Start

### Docker (Recommended)

1. **Build and start the API server:**
   ```bash
   docker-compose build xqsim-backend
   docker-compose up -d xqsim-backend
   ```

2. **Check server status:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Run a trace:**
   ```bash
   curl -X POST http://localhost:8000/trace \
     -H "Content-Type: application/json" \
     -d '{
       "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nh q[0];\ncx q[0],q[1];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];"
     }'
   ```

## API Documentation

### Endpoints

#### GET `/health`

Health check endpoint. Returns server status and limits.

**Response:**
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

#### POST `/trace`

Generates patch trace information from an OpenQASM 2.0 circuit.

**Request:**
```json
{
  "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\ncx q[0],q[1];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];",
  "config": "example_cmos_d5",
  "keep_artifacts": false,
  "debug_logging": false
}
```

**Parameters:**
- `qasm` (required): OpenQASM 2.0 circuit string
- `config` (optional): Configuration name from `src/configs/` (default: `"example_cmos_d5"`)
- `keep_artifacts` (optional): Keep intermediate files for debugging (default: `false`)
- `debug_logging` (optional): Enable debug logging (default: `false`)

**Response:**

The response includes:
- `meta`: Metadata (grid size, cycles, execution time, etc.)
- `input`: Input QASM information
- `compiled`: Compiled QISA instructions
- `patch`: Patch state information (initial state and events)
- `logical_qubit_mapping`: Logical qubit to patch mapping
- `clifford_t_execution_trace`: ⭐ **NEW** - Gate execution tracing (which gates caused which patch operations)

See [API Specification](./docs/FRONTEND_API_SPEC.md) for detailed response structure.

**Note:**
- Processing can take several minutes to over 10 minutes depending on circuit complexity
- Only one trace operation can run at a time (429 error if another is in progress)
- Timeout is set to 24 hours by default (configurable via environment variable)

## Configuration

Configuration files are located in `src/configs/`. They define:
- Architecture unit settings (QCP units, temperature, technology)
- Qubit plane parameters (code distance, error rates)
- Scalability constraints (gate latency, power budget)

Available configurations:
- `example_cmos_d5`
- `example_rsfq_d5`
- `current_300K_CMOS`
- `nearfuture_4K_CMOS`
- `nearfuture_4K_CMOS_Vopt`
- `nearfuture_4K_RSFQ`
- `future_4K_ERSFQ`

## Development

### Local Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run API server:**
   ```bash
   cd src
   uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
   ```

### Project Structure

```
.
├── src/
│   ├── api_server.py              # FastAPI server
│   ├── patch_trace_backend.py     # Core simulation logic
│   ├── configs/                   # Configuration files
│   ├── compiler/                  # Quantum compiler
│   ├── XQ-simulator/              # Simulator modules
│   └── XQ-estimator/              # Hardware estimation
├── docs/                          # API documentation
├── docker-compose.yml
└── Dockerfile
```

## Limitations

- Maximum qubits: 20 (configurable via `XQSIM_MAX_QUBITS`)
- Maximum QASM size: 1MB (configurable via `XQSIM_MAX_QASM_SIZE_BYTES`)
- Only one trace operation at a time
- Processing time can be long for complex circuits

## Publication

If you use XQsim in your research, please cite:

```
@inproceedings{byun2022xqsim,
    title={XQsim: modeling cross-technology control processors for 10+ K qubit quantum computers},
    author={Byun, Ilkwon and Kim, Junpyo and Min, Dongmoon and Nagaoka, Ikki and Fukumitsu, Kosuke and Ishikawa, Iori and Tanimoto, Teruo and Tanaka, Masamitsu and Inoue, Koji and Kim, Jangwoo},
    booktitle={Proceedings of the 49th Annual International Symposium on Computer Architecture},
    pages={366--382},
    year={2022}
}
```

## License

See [LICENSE](./LICENSE) file.

## Contributors

- [HPCS Lab](https://hpcs.snu.ac.kr), Seoul National University
