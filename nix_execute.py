import ctypes
import sys
import signal
import os
import time
import resource
import subprocess
import argparse


class nix_Process(object):
    def __init__(self, chained, memory_limit):
        self._chained = chained
        self.stdout = chained.stdout
        self.stdin = chained.stdin
        self.usages = None
        self.returncode = None
        self.memory_limit = memory_limit

    def __getattr__(self, name):
        if name in ["wait", "send_signal", "terminate", "kill"]:
            return getattr(self._chained, name)
        return object.__getattribute__(self, name)

    def poll(self):
        a = self._chained.poll()
        if a is not None:
            self.returncode = self._get_usages()[-1]
            return self.returncode
        return None

    def _get_usages(self):
        """
            Returns an array containing [bool tle, int max memory usage (kb), int runtime, int error code]
        """
        if not self.usages:
            self.usages = map(eval, self._chained.stderr.readline().split())
        return self.usages

    # TODO: implement this
    def get_rte(self):
        return False

    def get_tle(self):
        return self._get_usages()[0]

    def get_mle(self):
        return self._get_usages()[1] > self.memory_limit

    def get_execution_time(self):
        return self._get_usages()[2]

    def get_max_memory(self):
        return self._get_usages()[1]


def execute(path, time, memory):
    process = subprocess.Popen([sys.executable, __file__, '-t', str(time), '-m', str(memory), '--'] + path,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return nix_Process(process, memory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runs and monitors a process' usage stats on *nix systems")
    parser.add_argument("child_args", nargs="+", help="The child process path followed by arguments; relative allowed")
    parser.add_argument("-t", "--time", type=float, help="Time to limit process to, in seconds")
    parser.add_argument("-m", "--memory", type=int, help="Memory to limit process to, in kb")
    parser.add_argument("-ns", "--no-syscall", action='store_true', help="If specified, blocks system calls")
    parsed = parser.parse_args()

    child = parsed.child_args[0]
    child_args = parsed.child_args

    pid = None
    rusage = None
    code = None

    def sigchld(signum, frame):
        global code, rusage
        if pid is None:
            print 'Error'
            return
        _, code, rusage = os.wait4(pid, 0)

    h = signal.signal(signal.SIGCHLD, sigchld)
    pid = os.fork()
    if not pid:
        resource.setrlimit(resource.RLIMIT_AS, (parsed.memory * 1024 + 16 * 1024 * 1024,) * 2)
        #resource.setrlimit(resource.RLIMIT_NOFILE, (4, 4))
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))

        # Merge the stderr (2) into stdout (1) so that the execute
        # may be able to return usage stats through stderr
        os.dup2(1, 2)
        # Close all file descriptors that are not standard
        os.closerange(3, os.sysconf("SC_OPEN_MAX"))

        if parsed.no_syscall:
            libc = ctypes.CDLL('libc.so.6')
            PR_SET_SECCOMP = 22
            SECCOMP_MODE_SCTRICT = 1
            filter = '''sys_read: 1
    sys_write: (fd == 1) || (fd == 2)
    sys_exit: 1
    sys_exit_group: 1
    sys_mmap: 1
    on_next_syscall: 1'''
            if libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_SCTRICT):
                raise SystemError("SET_SECCOMP failed with %d" % ctypes.get_errno())

        # Replace current process with the child process
        # This call does not return
        os.execvp(child, child_args)
        # Unless it does, of course, in which case you're screwed
        # We don't cover this in the warranty
        #  When you reach here, you are screwed
        # As much as being handed control of a MySQL server without
        # ANY SQL knowledge or docs. ENJOY.
        os._exit(3306)
    else:
        sys.stdin.close()
        sys.stdout.close()
        start = time.time()
        time.sleep(parsed.time)
        duration = time.time() - start
        signal.signal(signal.SIGCHLD, h)
        tle = 0
        if code is None:  # TLE
            os.kill(pid, signal.SIGKILL)
            _, code, rusage = os.wait4(pid, 0)
            tle = 1
        print>> sys.stderr, tle, rusage.ru_maxrss, duration, code
