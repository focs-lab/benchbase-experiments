import sys
import os
import shutil
import yaml
import statistics

from subprocess import check_output, CalledProcessError, PIPE

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts")
EXPERIMENTS_DIR = os.path.join(os.getcwd(), sys.argv[1])
OUTPUT_DIR = os.path.join(os.getcwd(), sys.argv[2])

if not os.path.exists(OUTPUT_DIR):
    os.mkdir(OUTPUT_DIR)


tsans = [
    "sampling-base",
    "sampling-uclocks",
    "sampling-ol",
]

benchmarks = [
    "auctionmark",
    "chbenchmark",
    "epinions",
    "resourcestresser",
    "seats",
    "sibench",
    "smallbank",
    "tatp",
    "tpcc",
    # "tpch",
    "twitter",
    "voter",
    "wikipedia",
    "ycsb",
]


def parse_throughput(line):
    return float(line.split(b" requests/sec (throughput)")[0].split(b" = ")[-1])


means_out = open(os.path.join(OUTPUT_DIR, "avg.csv"), "w")
stdevs_out = open(os.path.join(OUTPUT_DIR, "stdev.csv"), "w")

means_out.write(f"Benchmark,{','.join(tsans)}\n")
stdevs_out.write(f"Benchmark,{','.join(tsans)}\n")

for bm in benchmarks:
    bm_means = []
    bm_stdevs = []
    for tsan in tsans:
        throughputs = []

        try:
            throughput_lines = check_output(f"grep -H throughput {EXPERIMENTS_DIR}/{bm}-{tsan}*/*.o*", shell=True, stderr=PIPE)
        except CalledProcessError:
            bm_means.append(0)
            bm_stdevs.append(0)
            continue

        for line in throughput_lines.splitlines():
            throughputs.append(parse_throughput(line))

        throughput_mean = 0
        throughput_stdev = 0
        if len(throughputs) == 0:
            throughput_mean = 0
        else:
            throughput_mean = statistics.mean(throughputs)

        if len(throughputs) <= 1:
            throughput_stdev = 0
        else:
            throughput_stdev = statistics.stdev(throughputs)

        bm_means.append(throughput_mean)
        bm_stdevs.append(throughput_stdev)

    means_out.write(f"{bm},{','.join(map(str, bm_means))}\n")
    stdevs_out.write(f"{bm},{','.join(map(str, bm_stdevs))}\n")
