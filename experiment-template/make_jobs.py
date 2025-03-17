import yaml
import os
import stat
import sys
import time
from subprocess import check_output, run, Popen, PIPE, STDOUT
import tempfile
from pathlib import Path
import shutil


if len(sys.argv) < 2:
    print(f"[!] Usage: {sys.argv[0]} <DESTINATION>")
    sys.exit(0)

DEST = Path(sys.argv[1])
if not DEST.exists():
    print(f"{DEST} does not exist. Aborting.")
    sys.exit(0)

CONFIG = yaml.safe_load(open(DEST / "config.yaml"))

BENCHMARKS = CONFIG["benchmarks"]
BUILDS = CONFIG["builds"]

START_JOBS_SCRIPT = "#!/bin/sh\n"

for benchmark in BENCHMARKS:
    BENCHMARK_PATH = DEST / benchmark
    if not BENCHMARK_PATH.exists():
        print(f"[!] {BENCHMARK_PATH} does not exist. Aborting.")
        sys.exit(0)

    BENCHMARK_PBS_SCRIPT = f"#PBS -N run-{benchmark}\n"
    BENCHMARK_PBS_SCRIPT += "#PBS -l walltime=24:00:00\n"
    BENCHMARK_PBS_SCRIPT += "#PBS -l select=1:ncpus=64:mem=128gb\n"
    BENCHMARK_PBS_SCRIPT += "#PBS -l place=excl\n"
    BENCHMARK_PBS_SCRIPT += "#PBS -P 31010020\n"
    BENCHMARK_PBS_SCRIPT += "#PBS -j oe\n"

    BENCHMARK_PBS_SCRIPT += f"cd {BENCHMARK_PATH.absolute()}\n"
    BENCHMARK_PBS_SCRIPT += f"./run.sh\n"

    BENCHMARK_PBS_SCRIPT_PATH = BENCHMARK_PATH / "job.pbs"
    open(BENCHMARK_PBS_SCRIPT_PATH, "w").write(BENCHMARK_PBS_SCRIPT)

    START_JOBS_SCRIPT += f"qsub {BENCHMARK_PBS_SCRIPT_PATH.absolute()}\n"

START_JOBS_SCRIPT_PATH = DEST / "start_jobs.sh"
open(START_JOBS_SCRIPT_PATH, "w").write(START_JOBS_SCRIPT)
os.system(f"chmod +x {START_JOBS_SCRIPT_PATH}")

    

