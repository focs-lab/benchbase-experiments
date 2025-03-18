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

BENCHMARKS = CONFIG["benchmarks"]
BUILDS = CONFIG["builds"]

WARMUP_RUN_DURATION = CONFIG["warmup-run-duration"]
WARMUP_RUN_MYSQL_BUILD = CONFIG["warmup-run-mysql-build"]

RUN_ALL_SCRIPT = "#!/bin/sh\n"

for benchmark in BENCHMARKS:
    # Setup the folder
    BENCHMARK_PATH = DEST / benchmark
    os.system(f"rm -rf {BENCHMARK_PATH}")
    BENCHMARK_PATH.mkdir()

    # The common stuff
    CONFIG2 = CONFIG.copy()
    CONFIG2["benchmark"] = benchmark

    TERMINALS = CONFIG["terminals"]
    WARMUP = CONFIG["warmup"]
    DURATION = CONFIG["duration"]

    BENCHMARK_CONFIG_PATH = CONFIGS_PATH / f"{benchmark}_config.xml"
    BENCHMARK_CONFIG = open(BENCHMARK_CONFIG_PATH, "r").read()

    BENCHMARK_RUN_SCRIPT = "#!/bin/sh\n"

    # Special warmup run
    if WARMUP_RUN_DURATION != 0:
        WARMUP_RUN_PATH = BENCHMARK_PATH / "warmup"
        os.system(f"rm -rf {WARMUP_RUN_PATH}")
        shutil.copytree(SCRIPTS_PATH, WARMUP_RUN_PATH)
        WARMUP_BENCHMARK_CONFIG = BENCHMARK_CONFIG
        WARMUP_BENCHMARK_CONFIG = WARMUP_BENCHMARK_CONFIG.replace("[[TERMINALS]]", str(TERMINALS))
        WARMUP_BENCHMARK_CONFIG = WARMUP_BENCHMARK_CONFIG.replace("[[WARMUP]]", str(0))
        WARMUP_BENCHMARK_CONFIG = WARMUP_BENCHMARK_CONFIG.replace("[[TPCH_WARMUP]]", str(0))
        WARMUP_BENCHMARK_CONFIG = WARMUP_BENCHMARK_CONFIG.replace("[[DURATION]]", str(WARMUP_RUN_DURATION))
        WARMUP_BENCHMARK_CONFIG = WARMUP_BENCHMARK_CONFIG.replace("[[TPCH_DURATION]]", str(int(WARMUP_RUN_DURATION / 3)))

        WARMUP_BENCHMARK_CONFIG_PATH = WARMUP_RUN_PATH / f"{benchmark}_config.xml"
        open(WARMUP_BENCHMARK_CONFIG_PATH, "w").write(WARMUP_BENCHMARK_CONFIG)

        WARMUP_CONFIG_PATH = WARMUP_RUN_PATH / f"config.yaml"
        CONFIG2["mysql-dist"] = f"dist-{WARMUP_RUN_MYSQL_BUILD}"
        yaml.safe_dump(CONFIG2, open(WARMUP_CONFIG_PATH, "w"))

        BENCHMARK_RUN_SCRIPT += f"(cd warmup; python3 runner.py; rm *raw*)\n"

    # For the actual experiments
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[TERMINALS]]", str(TERMINALS))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[WARMUP]]", str(WARMUP))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[TPCH_WARMUP]]", str(WARMUP))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[DURATION]]", str(DURATION))
    BENCHMARK_CONFIG = BENCHMARK_CONFIG.replace("[[TPCH_DURATION]]", str(int(DURATION / 3)))

    for build in BUILDS:
        EXPERIMENT_PATH = BENCHMARK_PATH / build
        os.system(f"rm -rf {EXPERIMENT_PATH}")
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

    RUN_ALL_SCRIPT += f"(cd {benchmark}; ./run.sh)\n"

RUN_ALL_SCRIPT_PATH = DEST / "run.sh"
open(RUN_ALL_SCRIPT_PATH, "w").write(RUN_ALL_SCRIPT)
os.system(f"chmod +x {RUN_ALL_SCRIPT_PATH}")
