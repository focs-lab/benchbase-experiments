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

THIS_SCRIPT_DIR = Path(__file__).parent
TEMPLATE_PATH = THIS_SCRIPT_DIR / "template"
SCRIPTS_PATH = TEMPLATE_PATH / "scripts"
CONFIGS_PATH = TEMPLATE_PATH / "configs"

CONFIG = yaml.safe_load(open(DEST / "config.yaml"))

BENCHMARKS = [
  "auctionmark",
  "epinions",
  "hyadapt",
  "noop",
  "resourcestresser",
  "seats",
  "sibench",
  "smallbank",
  "tatp",
  "tpcc",
  "tpch",
  "twitter",
  "voter",
  "wikipedia",
  "ycsb"
]

BUILDS = CONFIG["builds"]

for benchmark in BENCHMARKS:
    BENCHMARK_PATH = DEST / benchmark
    os.system(f"rm -rf {BENCHMARK_PATH}")
    BENCHMARK_PATH.mkdir()

    BENCHMARK_CONFIG_PATH = CONFIGS_PATH / f"{benchmark}_config.xml"
    BENCHMARK_CONFIG = open(BENCHMARK_CONFIG_PATH, "r").read()

    TERMINALS = CONFIG["terminals"]
    WARMUP = CONFIG["warmup"]
    DURATION = CONFIG["duration"]

    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[TERMINALS]]", str(TERMINALS))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[WARMUP]]", str(WARMUP))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[TPCH_WARMUP]]", str(WARMUP))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[DURATION]]", str(DURATION))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[TPCH_DURATION]]", str(int(DURATION / 3)))

    CONFIG2 = CONFIG.copy()
    CONFIG2["benchmark"] = benchmark

    BENCHMARK_RUN_SCRIPT = "#!/bin/sh\n"

    for build in BUILDS:
        EXPERIMENT_PATH = BENCHMARK_PATH / build
        shutil.copytree(SCRIPTS_PATH, EXPERIMENT_PATH)

        EXPERIMENT_BENCHMARK_CONFIG_PATH = EXPERIMENT_PATH / f"{benchmark}_config.xml"
        open(EXPERIMENT_BENCHMARK_CONFIG_PATH, "w").write(BENCHMARK_CONFIG)

        EXPERIMENT_CONFIG_PATH = EXPERIMENT_PATH / f"config.yaml"
        CONFIG2["mysql-dist"] = f"dist-{build}"
        yaml.safe_dump(CONFIG2, open(EXPERIMENT_CONFIG_PATH, "w"))

        BENCHMARK_RUN_SCRIPT += f"(cd {build}; python3 runner.py; rm *raw*)\n"

    BENCHMARK_RUN_SCRIPT_PATH = BENCHMARK_PATH / "run.sh"
    open(BENCHMARK_RUN_SCRIPT_PATH, "w").write(BENCHMARK_RUN_SCRIPT)
    os.system(f"chmod +x {BENCHMARK_RUN_SCRIPT_PATH}")
    

