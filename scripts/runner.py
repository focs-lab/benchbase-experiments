import yaml
import os
import time
from subprocess import check_output, run, Popen, PIPE, STDOUT
import tempfile

def write(proc: Popen, command):
    proc.stdin.write(f"{command}\n".encode())
    proc.stdin.flush()

CONFIG = yaml.load(open("config.yaml"), Loader=yaml.BaseLoader)
WORKSPACE = tempfile.TemporaryDirectory(dir=CONFIG["workspace"])
CWD = os.getcwd()

MYSQL_DIST_PATH = os.path.join(CONFIG["mysql"], CONFIG["mysql-dist"])
MYSQL_DIST_NO_TSAN_PATH = os.path.join(CONFIG["mysql"], CONFIG["mysql-dist-no-tsan"])
MYSQLD_NO_TSAN_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysqld")
MYSQLD_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysqld")
MYSQL_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysql")
MYSQL_DATA_PATH = os.path.join(WORKSPACE.name, "mysql-data")

BENCHBASE_PATH = CONFIG["benchbase"]
BENCHBASE_MYSQL_PATH = os.path.join(BENCHBASE_PATH, "target", "benchbase-mysql")
BENCHMARK_NAME = CONFIG["benchmark"]
BB_CONFIG_PATH = os.path.join(CWD, f'{BENCHMARK_NAME}_config.xml')

RNG_SEED = CONFIG["seed"]

print("[+] Initializing MYSQL data.")
mysqld = Popen([MYSQLD_PATH, "--initialize", f"--basedir={MYSQL_DIST_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT)

MYSQL_PASSWORD = None
while MYSQL_PASSWORD is None:
    line = mysqld.stdout.readline()
    if b"password" in line.lower():
        print(line.decode())
        MYSQL_PASSWORD = line.strip().split(b"root@localhost: ")[1].decode()
print("[*] MYSQL password:", MYSQL_PASSWORD)
mysqld.wait()

print("[+] Starting MYSQL server (no tsan) for database creation.")
mysqld = Popen([MYSQLD_NO_TSAN_PATH, f"--basedir={MYSQL_DIST_NO_TSAN_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT)
while True:
    line = mysqld.stdout.readline()
    print(line.decode())
    if b"mysql.sock" in line.lower() or line == b"":
        break

# somehow --connect-expired-password is necessary for doing this
os.system(f"{MYSQL_PATH} --connect-expired-password -u root \"-p{MYSQL_PASSWORD}\" < init.sql")

benchbase_setup = run(f"java -jar benchbase.jar -b {BENCHMARK_NAME} -c {BB_CONFIG_PATH} --create=true --load=true".split(" "),
                      cwd=BENCHBASE_MYSQL_PATH)

print("[+] Shutdown mysqld server (no tsan).")
os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")
mysqld.wait()

print("[+] Starting MYSQL server (version under test) for benchmarking.")
mysqld = Popen([MYSQLD_PATH, f"--basedir={MYSQL_DIST_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT,
               env={"TSAN_OPTIONS": f"report_bugs=0 detect_deadlocks=0 sampling_rng_seed={RNG_SEED}"})
while True:
    line = mysqld.stdout.readline()
    print(line.decode())
    if b"mysql.sock" in line.lower() or line == b"":
        break

vtune = Popen("bash", stdin=PIPE, stdout=PIPE, stderr=STDOUT, )
write(vtune, "source /app/apps/oneapi/2022.1.2/setvars.sh")
write(vtune, "vtune -collect hotspots -knob sampling-mode=sw -target-pid $(pidof mysqld) -run-pass-thru=--no-altstack -duration=300")
while True:
    line = vtune.stdout.readline()
    print(line)
    if b"Collection started" in line or line == b"":
        break

benchbase_execute = run(["java", "-jar", "benchbase.jar", "-b", BENCHMARK_NAME, "-c", BB_CONFIG_PATH, "--execute=true", "-d", CWD],
                          cwd=BENCHBASE_MYSQL_PATH)

while True:
    line = vtune.stdout.readline()
    print(line.decode())
    if b"100 % done" in line or line == b"":
        break

os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")
mysqld.wait()

# cleanup
WORKSPACE.cleanup()
