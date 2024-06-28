import yaml
import os
import time
from subprocess import check_output, run, Popen, PIPE, STDOUT
import tempfile

def write(proc: Popen, command):
    proc.stdin.write(f"{command}\n".encode())
    proc.stdin.flush()

CWD = os.getcwd()
CONFIG = yaml.load(open("config.yaml"), Loader=yaml.BaseLoader)

MYSQL_DIST_PATH = os.path.join(CONFIG["mysql"], CONFIG["mysql-dist"])
MYSQL_DIST_NO_TSAN_PATH = os.path.join(CONFIG["mysql"], CONFIG["mysql-dist-no-tsan"])
MYSQLD_NO_TSAN_PATH = os.path.join(MYSQL_DIST_NO_TSAN_PATH, "bin/mysqld")
MYSQLD_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysqld")
MYSQL_PATH = os.path.join(MYSQL_DIST_PATH, "bin/mysql")

BENCHBASE_PATH = CONFIG["benchbase"]
BENCHBASE_MYSQL_PATH = os.path.join(BENCHBASE_PATH, "target", "benchbase-mysql")
BENCHMARK_NAME = CONFIG["benchmark"]
BB_CONFIG_PATH = os.path.join(CWD, f'{BENCHMARK_NAME}_config.xml')


WORKSPACE = tempfile.TemporaryDirectory(dir=CONFIG["workspace"])
MYSQL_DATA_PATH = os.path.join(WORKSPACE.name, "mysql-data")


RNG_SEED = CONFIG["seed"]

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

benchmark_parameter = BENCHMARK_NAME
if benchmark_parameter == "chbenchmark":
    benchmark_parameter = "tpcc,chbenchmark"
benchbase_setup = run(f"java -jar benchbase.jar -b {benchmark_parameter} -c {BB_CONFIG_PATH} --create=true --load=true".split(" "),
                      cwd=BENCHBASE_MYSQL_PATH)

print("[+] Shutdown mysqld server (no tsan).")
os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")
mysqld.wait()

print("[+] Starting MYSQL server (version under test) for benchmarking.")
mysqld = Popen([MYSQLD_PATH, f"--basedir={MYSQL_DIST_PATH}", f"--datadir={MYSQL_DATA_PATH}"], stdout=PIPE, stderr=STDOUT,
               env={"TSAN_OPTIONS": f"ignore_noninstrumented_modules=0 report_bugs=0 detect_deadlocks=0 sampling_rng_seed={RNG_SEED}"})
while True:
    line = mysqld.stdout.readline()
    print(line.decode().strip())
    if b"mysql.sock" in line.lower() or line.strip() == b"":
        break

# Now we dont want to allow so many connections. Reset it to the default (151)
os.system(f"{MYSQL_PATH} -u root -p1 < reset_max_conns.sql")

# vtune = Popen("bash", stdin=PIPE, stdout=PIPE, stderr=STDOUT, )
# write(vtune, "source /app/apps/oneapi/2022.1.2/setvars.sh")
# write(vtune, "vtune -collect hotspots -knob sampling-mode=sw -target-pid $(pidof mysqld) -run-pass-thru=--no-altstack -duration=300")
# while True:
#     line = vtune.stdout.readline()
#     print(line.decode().strip())
#     if b"Collection started" in line or line.strip() == b"":
#         break

benchbase_execute = run(["timeout", str(3900), "java", "-jar", "benchbase.jar", "-b", benchmark_parameter, "-c", BB_CONFIG_PATH, "--execute=true", "-d", CWD],
                          cwd=BENCHBASE_MYSQL_PATH)

# while True:
#     line = vtune.stdout.readline()
#     print(line.decode().strip())
#     if b"100 % done" in line or line.strip() == b"":
#         break

# write(vtune, "vtune -report summary -format csv > summary.csv")
# write(vtune, "vtune -report hotspots -format csv > hotspots.csv")
# write(vtune, "echo vtune finished!")

# while True:
#     line = vtune.stdout.readline()
#     if b"vtune finished!" in line or line.strip() == b"":
#         break
#     print(line.decode().strip())


# cleanup
os.system(f"{MYSQL_PATH} -u root -p1 < shutdown.sql")
mysqld.wait()
WORKSPACE.cleanup()
