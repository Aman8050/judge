import os
import subprocess

from dmoj.executors.java_executor import JavaExecutor


class Executor(JavaExecutor):
    name = 'SCALA'
    ext = '.scala'

    compiler = 'scalac'
    vm = 'scala_vm'

    test_program = '''\
object self_test {
  def main(args: Array[String]) {
    println("echo: Hello, World!")
  }
}
'''

    def create_files(self, problem_id, source_code, *args, **kwargs):
        super(Executor, self).create_files(problem_id, source_code, *args, **kwargs)
        self._class_name = problem_id

    def get_cmdline(self):
        res = super(Executor, self).get_cmdline()

        # Simply run bash -x $(which scala) and copy all arguments after -Xmx and -Xms
        # and add it as a list in the configuration.
        res[-2:-1] = self.runtime_dict['scala_args']
        return res

    def get_compile_args(self):
        return [self.get_compiler(), self._code]

    @classmethod
    def get_versionable_commands(cls):
        return [('scalac', cls.get_compiler()), ('java', cls.get_vm())]

    @classmethod
    def autoconfig(cls):
        result = {}

        for key, files in {'scalac': ['scalac'], 'scala': ['scala']}.iteritems():
            file = cls.find_command_from_list(files)
            if file is None:
                return result, False, 'Failed to find "%s"' % key
            result[key] = file

        scala = result.pop('scala')
        with open(os.devnull, 'w') as devnull:
            process = subprocess.Popen(['bash', '-x', scala, '-version'], stdout=devnull, stderr=subprocess.PIPE)
        log = [i for i in process.communicate()[1].split('\n') if 'scala.tools.nsc.MainGenericRunner' in i]

        if not log:
            return result, False, 'Failed to parse: %s' % scala

        cmdline = log[-1].lstrip('+ ').split()
        result['scala_vm'] = cls.unravel_java(cls.find_command_from_list([cmdline[0]]))
        result['scala_args'] = [i for i in cmdline[1:-1] if not i.startswith(('-Xmx', '-Xms'))]

        data = cls.autoconfig_run_test(result)
        if data[1]:
            data = data[:2] + ('Using %s' % scala,) + data[3:]
        return data
