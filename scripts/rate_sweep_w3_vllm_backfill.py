"""
Backfill vLLM rate sweep for W3 workload (p512d20 + p512d50, 70/30).

Reuses the same Vidur + A100 + Llama-3-8B setting as
scripts/rate_sweep_perseg_gate.py, writes to the same SQL table
(rate_sweep_perseg) so Figure C can query a uniform source.

Rates: 12..36 (matches existing Sarathi / WAIT coverage).
Per-rate nreq: 20000 — larger than the earlier Sarathi/WAIT sweeps
(which used 5000) to give a tighter steady-state estimate. Vidur's
built-in SimulationMemoryManager (vidur/simulator.py:49) runs every
500 completions, so long single-rate runs stay within bounded RSS.

Usage on VM:
  cd /persistent/vidur_or
  nohup python -u scripts/rate_sweep_w3_vllm_backfill.py > w3_vllm.log 2>&1 &

Each rate runs in an isolated subprocess so parent-process memory stays
bounded; an explicit gc pass + 1s sleep between rates keeps long runs
steady.
"""
import subprocess, json, pandas as pd, os, shutil, glob, sqlite3, tempfile, sys
import gc, time
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB = str(PROJECT / "experiments.db")

NREQ = 20000

COMMON = [
    "python", "-m", "vidur.main",
    "--replica_config_device", "a100",
    "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
    "--replica_config_memory_margin_fraction", "0.1",
    "--cluster_config_num_replicas", "1",
    "--replica_config_tensor_parallel_size", "1",
    "--replica_config_num_pipeline_stages", "1",
    "--request_generator_config_type", "custom",
    "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
    "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
    "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
    "--no-metrics_config_store_plots",
]

W3 = {
    "types": [
        {"type": "short", "prefill": 512, "decode": 20, "arrival_rate_frac": 0.7},
        {"type": "long",  "prefill": 512, "decode": 50, "arrival_rate_frac": 0.3},
    ],
    "max_tokens": 562,
    "rates": list(range(12, 37)),
}


def make_prompt_types(rate):
    return json.dumps([
        {"type": t["type"], "prefill": t["prefill"], "decode": t["decode"],
         "arrival_rate": round(rate * t["arrival_rate_frac"], 2)}
        for t in W3["types"]
    ])


def already_done(cn, algorithm, config_name, rate):
    r = cn.execute(
        "SELECT 1 FROM rate_sweep_perseg "
        "WHERE workload=? AND algorithm=? AND config_name=? AND arrival_rate=? LIMIT 1",
        ("W3", algorithm, config_name, rate),
    ).fetchone()
    return r is not None


def run_sim(extra_args, nreq=NREQ):
    tmpdir = tempfile.mkdtemp(prefix="vidur_w3_vllm_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "off"
    cmd = COMMON + [
        "--custom_request_generator_config_num_requests", str(nreq),
        "--metrics_config_output_dir", tmpdir,
    ] + extra_args
    try:
        # 7200s = 2h per rate. nreq=20000 with unstable r=22+ extends
        # simulation tail; the previous 1800s budget was for nreq=5000.
        result = subprocess.run(
            cmd, capture_output=True, cwd=str(PROJECT), timeout=7200,
            env=env, text=True,
        )
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT 7200s] tmpdir={tmpdir}", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    if result.returncode != 0:
        print(f"[FAIL rc={result.returncode}] stderr tail:\n{result.stderr[-400:]}",
              flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    df = pd.read_csv(csvs[0])
    shutil.rmtree(tmpdir, ignore_errors=True)
    start = len(df) // 4
    end = max(start + 1, len(df) - 500)
    s = df.iloc[start:end]
    mean_e2e = s["request_e2e_time"].mean()
    p99_e2e = s["request_e2e_time"].quantile(0.99)
    n_steady = len(s)
    # Release memory before returning so parent stays bounded across rates.
    del df, s
    gc.collect()
    return mean_e2e, p99_e2e, n_steady


def main():
    cn = sqlite3.connect(DB)
    cn.execute("""CREATE TABLE IF NOT EXISTS rate_sweep_perseg (
        timestamp TEXT, workload TEXT, algorithm TEXT, config_name TEXT,
        arrival_rate REAL, total_limit INT, chunk_size INT, seg_margin REAL,
        nreq INT, mean_latency REAL, p99_latency REAL, n_steady INT
    )""")
    cn.commit()

    print("=== W3 vLLM backfill ===", flush=True)
    for rate in W3["rates"]:
        if already_done(cn, "vllm", "vLLM", rate):
            row = cn.execute(
                "SELECT mean_latency FROM rate_sweep_perseg "
                "WHERE workload='W3' AND algorithm='vllm' AND arrival_rate=?",
                (rate,),
            ).fetchone()
            print(f"r={rate:2d} vLLM={row[0]:.3f}s [cached]", flush=True)
            continue

        pt = make_prompt_types(rate)
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", str(W3["max_tokens"]),
            "--replica_scheduler_config_type", "vllm",
        ])
        if res is None:
            print(f"r={rate:2d} vLLM FAIL", flush=True)
            continue
        m, p99, n = res
        cn.execute(
            "INSERT INTO rate_sweep_perseg VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(), "W3", "vllm", "vLLM",
             rate, None, None, 0, NREQ, m, p99, n),
        )
        cn.commit()
        print(f"r={rate:2d} vLLM={m:.3f}s  p99={p99:.3f}s  n_steady={n}", flush=True)
        # Inter-rate cleanup: release file handles / temp buffers.
        gc.collect()
        time.sleep(1.0)

    cn.close()
    print("Done.")


if __name__ == "__main__":
    main()
