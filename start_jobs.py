import sys
import os
import shutil
import yaml

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts")
EXPERIMENTS_DIR = os.path.join(os.getcwd(), sys.argv[1])

COUNT = 5

tsans = [
    "sampling-base",
    "sampling-uclocks",
    "sampling-ol",
]

benchmarks = [
    # "tpcc",
    "twitter",
    "voter",
    "ycsb",
    "smallbank",
]

for _ in range(COUNT):
    for bm in benchmarks:
        for tsan in tsans:
            idx = 0
            exp_dir = os.path.join(EXPERIMENTS_DIR, f"{bm}-{tsan}-{idx}")

            while os.path.exists(exp_dir):
                idx += 1
                exp_dir = os.path.join(EXPERIMENTS_DIR, f"{bm}-{tsan}-{idx}")

            print(TEMPLATE_DIR)
            print(exp_dir)
            shutil.copytree(TEMPLATE_DIR, exp_dir)

            config_path = os.path.join(exp_dir, "config.yaml")
            config = yaml.load(open(config_path), Loader=yaml.BaseLoader)
            config["seed"] = idx + 1234
            config["mysql-dist"] = f"dist-tsan-{tsan}"
            config["benchmark"] = bm
            yaml.dump(config, open(config_path, "w"))

            pbs_path = os.path.join(exp_dir, "job.pbs")
            pbs = open(pbs_path).read()
            pbs = pbs.replace("#PBS -N mysql", f"#PBS -N {bm}-{tsan}")
            open(pbs_path, "w").write(pbs)

            os.system(f"cd {exp_dir}; qsub job.pbs")

