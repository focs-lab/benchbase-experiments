import sys
import yaml
import os
import time
from subprocess import check_output, run, Popen, PIPE, STDOUT
import tempfile
from datetime import datetime

def write(proc: Popen, command):
    proc.stdin.write(f"{command}\n".encode())
    proc.stdin.flush()

CWD = os.getcwd()
CONFIG = yaml.load(open("config2.yaml"), Loader=yaml.BaseLoader)

MYSQL_DIST_NO_TSAN_PATH = os.path.join(CONFIG["mysql"], "dist-no-tsan")
MYSQLD_NO_TSAN_PATH = os.path.join(MYSQL_DIST_NO_TSAN_PATH, "bin/mysqld")
MYSQL_PATH = os.path.join(MYSQL_DIST_NO_TSAN_PATH, "bin/mysql")

BENCHBASE_PATH = CONFIG["benchbase"]
BENCHBASE_MYSQL_PATH = os.path.join(BENCHBASE_PATH, "target", "benchbase-mysql")
BENCHMARK_NAME = CONFIG["benchmark"]
BB_CONFIG_PATH = os.path.join(CWD, f'{BENCHMARK_NAME}_config.xml')

RNG_SEED = int(CONFIG["seed"])

LOG_FILE = open("log.txt", "w")

for count in range(100):
    for dist in CONFIG["mysql-dists"]:
        now = datetime.now()
        dts = now.strftime("%d/%m/%Y %H:%M:%S")
        LOG_FILE.write(f"[{dts}]: {dist}-{count}\n")
        LOG_FILE.flush()

        WORKSPACE = tempfile.TemporaryDirectory(dir=CONFIG["workspace"])
        MYSQL_DATA_PATH = os.path.join(WORKSPACE.name, "mysql-data")

        MYSQL_DIST_PATH = os.path.join(CONFIG["mysql"], f"dist-{dist}")
        MYSQLD_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysqld")

        print("[+] Initializing MYSQL data.")
        mysqld = Popen([MYSQLD_PATH, "--initialize", f"--basedir={MYSQL_DIST_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT)

        MYSQL_PASSWORD = None
        while MYSQL_PASSWORD is None:
            line = mysqld.stdout.readline()
            print(line.decode().strip())
            if b"password" in line.lower() or line.strip() == b"":
                MYSQL_PASSWORD = line.strip().split(b"root@localhost: ")[1].decode()
        print("[*] MYSQL password:", MYSQL_PASSWORD)
        mysqld.wait()

        print("[+] Starting MYSQL server (no tsan) for database creation.")
        mysqld = Popen([MYSQLD_NO_TSAN_PATH, f"--basedir={MYSQL_DIST_NO_TSAN_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT)
        while True:
            line = mysqld.stdout.readline()
            print(line.decode().strip())
            if b"mysql.sock" in line.lower() or line.strip() == b"":
                break

        # somehow --connect-expired-password is necessary for doing this
        os.system(f"{MYSQL_PATH} --connect-expired-password -u root \"-p{MYSQL_PASSWORD}\" < init.sql")

        # Create tables and load data into table
        benchbase_setup = run(f"java -jar benchbase.jar -b {BENCHMARK_NAME} -c {BB_CONFIG_PATH} --create=true --load=true".split(" "),
                            cwd=BENCHBASE_MYSQL_PATH)

        print("[+] Shutdown mysqld server (no tsan).")
        os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")
        mysqld.wait()

        print("[+] Starting MYSQL server (version under test) for benchmarking.")
        RESULTS_DIR = os.path.join(CWD, "results", f"{dist}-{count}")
        if not os.path.exists(RESULTS_DIR):
            os.makedirs(RESULTS_DIR)
        OUTPUT_FILE = open(os.path.join(RESULTS_DIR, "output.txt"), "wb")
        mysqld = Popen([MYSQLD_PATH, f"--basedir={MYSQL_DIST_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT,
                    env={"TSAN_OPTIONS": f"ignore_noninstrumented_modules=0 report_bugs=0 halt_on_error=0 detect_deadlocks=0 sampling_rng_seed={RNG_SEED+count}"})
        while True:
            line = mysqld.stdout.readline()
            print(line.decode().strip())
            if b"mysql.sock" in line.lower() or line.strip() == b"":
                break

        # Now we dont want to allow so many connections. Reset it to the default (151)
        os.system(f"{MYSQL_PATH} -u root -p1 < reset_max_conns.sql")

        # Run the benchmark, put a timeout of 1hr5mins in case it hangs
        benchbase_execute = run(["timeout", str(3900), "java", "-jar", "benchbase.jar", "-b", BENCHMARK_NAME, "-c", BB_CONFIG_PATH, "--execute=true", "-d", RESULTS_DIR],
                                cwd=BENCHBASE_MYSQL_PATH)

        # cleanup
        os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")

        for line in mysqld.stdout:
            if len(line) == 0:
                break
            print(line.decode().strip())
            if b"ThreadSanitizer: reported" in line:
                OUTPUT_FILE.write(line)
            elif b"[BASE]" in line or b"[UCLOCKS]" in line or b"[OL]" in line:
                OUTPUT_FILE.write(line)

        OUTPUT_FILE.close()
        mysqld.wait()
        WORKSPACE.cleanup()

LOG_FILE.close()
