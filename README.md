# Scripts for Running BenchBase with MySQL

This simple repository provides helper scripts for conveniently running experiments that compares the performance of different MySQL Server builds.
Specifically, this is for comparing different builds of MySQL Server compiled using different versions of TSan.
Thus, some configuration parameters will be related to TSan. 

## Get the files

Just clone this repo.

```
git clone https://github.com/focs-lab/benchbase-experiments/
```

## Prerequisites

See the build instructions for [mysql](others/mysql/README.md) and [benchbase](others/benchbase/README.md).

## Setup experiments

To set up an experiment, first create a folder that will contain all the experiment files.
E.g.

```
mkdir experiment
```

Then, create a config file. You may copy the sample below and modify it accordingly.

```yaml
benchbase: /home/vagrant/benchbase
mysql: /home/vagrant/mysql/mysql-server-mysql-8.0.39
mysql-dist-no-tsan: dist-nt
workspace: /home/vagrant/benchbase-experiments/workspace
symbolizer: /home/vagrant/llvm-project/build/bin/llvm-symbolizer
seed: 1234
report-bugs: 0

duration: 3600
warmup: 120
terminals: 3

builds:
- nt
- t
- e
- st-03
- st-3
- st-10
- su-03
- su-3
- su-10
- so-03
- so-3
- so-10

warmup-run-duration: 60
warmup-run-mysql-build: nt

benchmarks:
- auctionmark
- epinions
- hyadapt
- noop
- resourcestresser
- seats
- sibench
- smallbank
- tatp
- tpcc
- tpch
- twitter
- voter
- wikipedia
- ycsb
```

The purposes of each of the fields above are as given below:
- `benchbase`: Path to BenchBase, as cloned from https://github.com/cmu-db/benchbase. It should already be built.
- `mysql`: Path to the MySQL folder where the built/installed files reside.
- `mysql-dist-no-tsan`: Path to the folder that contains MySQL built without TSan. This path is relative to the path in `mysql` above.
- `workspace`: Path to a folder for storing the MySQL database and other temporary files when the experiment is running. It should already exist.
- `symbolizer`: Path to the LLVM symbolizer.
- `duration`: Duration of each benchmarking run.
- `warmup`:  Duration for warmup before starting a benchmarking run.
- `terminals`: Number of terminals that BenchBase will use in a benchmarking run. It is mainly to control the concurrent load on the MySQL Server.
  - If it is too low, it exposes little concurrency, and experiments for algorithms that work well on concurrent benchmarks will see less prominent results.
  - If it is too high, the server will be overloaded, resulting in OS-level noise (that affects the evaluation of an algorithm) due to frequent context switching or waiting for other threads.
  - From experience, taking around 1/5 or 1/6 of the number of CPUs seem to work well.
- `builds`: List of MySQL builds that are to be benchmarked.
  - The corresponding builds should be stored in a folder with the name prefixed with "dist-".
  - For example, if `st-03` is in the list, `dist-st-03` must be present in the path denoted in `mysql`, and should be a MySQL install destination (according to `cmake --install <build folder> --prefix <install destination>`).
- `warmup-run-duration`: Duration for an extra run that occurs before the first run, in case one wants a longer warmup before the first run.
- `warmup-run-mysql-build`: MySQL build for that extra warmup run. Since the results should not matter, perhaps choose the fastest build so that it can achieve the best "warming up" effect.
- `benchmarks`: Benchmarks to run the experiment on. The available list of benchmarks are in the sample config above.

