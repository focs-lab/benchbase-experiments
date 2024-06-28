import sys
import os
import shutil
import yaml

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts")
EXPERIMENTS_DIR = os.path.join(os.getcwd(), sys.argv[1])

COUNT = 1
SEED_OFFSET = 1234

TIME = 3600
TERMINALS = 28
NCPUS = 64
MEMORY = 64

tsans = [
    # "sampling-base",
    # "sampling-uclocks",
    "sampling-ol",
]

benchmarks = [
    "auctionmark",
    "epinions",
    "seats",
    "sibench",
    "smallbank",
    "tatp",
    "tpcc",
    "twitter",
    "voter",
    "wikipedia",
    "ycsb",
]

for count in range(COUNT):
    for bm in benchmarks:
        for tsan in tsans:
            idx = count
            exp_dir = os.path.join(EXPERIMENTS_DIR, f"{bm}-{tsan}-{idx}")

            while os.path.exists(exp_dir):
                idx += 1
                exp_dir = os.path.join(EXPERIMENTS_DIR, f"{bm}-{tsan}-{idx}")

            print(TEMPLATE_DIR)
            print(exp_dir)
            shutil.copytree(TEMPLATE_DIR, exp_dir)

            config_path = os.path.join(exp_dir, "config.yaml")
            config = yaml.load(open(config_path), Loader=yaml.BaseLoader)
            config["seed"] = count + SEED_OFFSET
            config["mysql-dist"] = f"dist-tsan-{tsan}"
            config["benchmark"] = bm
            yaml.dump(config, open(config_path, "w"))

            pbs_path = os.path.join(exp_dir, "job.pbs")
            pbs = open(pbs_path).read()
            pbs = pbs.replace("#PBS -l select=1:ncpus=128:mem=64gb", f"#PBS -l select=1:ncpus={NCPUS}:mem={MEMORY}gb")
            pbs = pbs.replace("#PBS -N mysql", f"#PBS -N {bm}-{tsan}-{idx}")
            open(pbs_path, "w").write(pbs)

            bb_config_path = os.path.join(exp_dir, f"{bm}_config.xml")
            bb_config = open(bb_config_path).read()
            bb_config = bb_config.replace("<time>3600</time>", f"<time>{TIME}</time>")
            bb_config = bb_config.replace("<terminals>60</terminals>", f"<terminals>{TERMINALS}</terminals>")
            open(bb_config_path, "w").write(bb_config)

            os.system(f"cd {exp_dir}; qsub job.pbs")

