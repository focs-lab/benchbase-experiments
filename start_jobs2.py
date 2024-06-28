import sys
import os
import shutil
import yaml

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts")
EXPERIMENTS_DIR = os.path.join(os.getcwd(), sys.argv[1])

SEED_OFFSET = 5678

TIME = 3600

benchmarks = [
    "auctionmark",
    "epinions",
    "seats",
    "sibench",
    "smallbank",
    "tatp",
    # "tpcc",
    "twitter",
    "voter",
    # "wikipedia",
    "ycsb",
]

for bm in benchmarks:
    exp_dir = os.path.join(EXPERIMENTS_DIR, f"{bm}")

    print(TEMPLATE_DIR)
    print(exp_dir)
    shutil.copytree(TEMPLATE_DIR, exp_dir)

    config_path = os.path.join(exp_dir, "config2.yaml")
    config = yaml.load(open(config_path), Loader=yaml.BaseLoader)
    config["seed"] = SEED_OFFSET
    config["benchmark"] = bm
    yaml.dump(config, open(config_path, "w"))

    pbs_path = os.path.join(exp_dir, "job2.pbs")
    pbs = open(pbs_path).read()
    pbs = pbs.replace("#PBS -N mysql", f"#PBS -N {bm}")
    open(pbs_path, "w").write(pbs)

    bb_config_path = os.path.join(exp_dir, f"{bm}_config.xml")
    bb_config = open(bb_config_path).read()
    bb_config = bb_config.replace("<time>3600</time>", f"<time>{TIME}</time>")
    open(bb_config_path, "w").write(bb_config)

    os.system(f"cd {exp_dir}; qsub job2.pbs")

