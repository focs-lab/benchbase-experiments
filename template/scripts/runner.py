import yaml
import os
import time
from subprocess import check_output, run, Popen, PIPE, STDOUT
import tempfile

def write(proc: Popen, command):
    proc.stdin.write(f"{command}\n".encode())
    proc.stdin.flush()

CWD = os.getcwd()
CONFIG = yaml.safe_load(open("config.yaml"))

MYSQL_DIST_PATH = os.path.join(CONFIG["mysql"], CONFIG["mysql-dist"])
MYSQL_DIST_NO_TSAN_PATH = os.path.join(CONFIG["mysql"], CONFIG["mysql-dist-no-tsan"])
MYSQLD_NO_TSAN_PATH = os.path.join(MYSQL_DIST_NO_TSAN_PATH, "bin/mysqld")
MYSQLD_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysqld")
MYSQL_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysql")

SYMBOLIZER_PATH = CONFIG["symbolizer"]

BENCHBASE_PATH = CONFIG["benchbase"]
BENCHBASE_MYSQL_PATH = os.path.join(BENCHBASE_PATH, "target", "benchbase-mysql")
BENCHMARK_NAME = CONFIG["benchmark"]
BB_CONFIG_PATH = os.path.join(CWD, f'{BENCHMARK_NAME}_config.xml')

WORKSPACE = tempfile.TemporaryDirectory(dir=CONFIG["workspace"])
MYSQL_DATA_PATH = os.path.join(WORKSPACE.name, "mysql-data")

RNG_SEED = CONFIG["seed"]
REPORT_BUGS = CONFIG["report-bugs"]
WARMUP = int(CONFIG["warmup"])
DURATION = int(CONFIG["duration"])

print("[+] Initializing MYSQL data.")
mysqld = Popen([MYSQLD_NO_TSAN_PATH, "--initialize", f"--basedir={MYSQL_DIST_NO_TSAN_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT)

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

benchmark_parameter = BENCHMARK_NAME
if benchmark_parameter == "chbenchmark":
    benchmark_parameter = "tpcc,chbenchmark"
benchbase_setup = run(f"java -jar benchbase.jar -b {benchmark_parameter} -c {BB_CONFIG_PATH} --create=true --load=true".split(" "),
                      cwd=BENCHBASE_MYSQL_PATH)

print("[+] Shutdown mysqld server (no tsan).")
os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")
mysqld.wait()

import datetime
dts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
mysql_out_path = f"{dts}.mysqld.log"
mysql_out = open(mysql_out_path, "w")

print("[+] Starting MYSQL server (version under test) for benchmarking.")
mysqld = Popen([MYSQLD_PATH, f"--basedir={MYSQL_DIST_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=mysql_out, stderr=STDOUT,
               env={"TSAN_OPTIONS": f"ignore_noninstrumented_modules=0 report_bugs={REPORT_BUGS} external_symbolizer_path={SYMBOLIZER_PATH} detect_deadlocks=0 sampling_rng_seed={RNG_SEED}"})
while True:
   output = open(mysql_out_path).read()
   if "mysql.sock" in output.lower():
       break

# Now we dont want to allow so many connections. Reset it to the default (151)
os.system(f"{MYSQL_PATH} -u root -p1 < reset_max_conns.sql")

benchbase_execute = run(["timeout", str(DURATION + WARMUP*3 + 1800), "java", "-jar", "benchbase.jar", "-b", benchmark_parameter, "-c", BB_CONFIG_PATH, "--execute=true", "-d", CWD],
                          cwd=BENCHBASE_MYSQL_PATH)

# cleanup
os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")

mysql_out.close()
mysqld.wait()
WORKSPACE.cleanup()
