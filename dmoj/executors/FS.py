import os

from dmoj.executors.utils import test_executor
from dmoj.conf import env
from .clr_executor import CLRExecutor


class Executor(CLRExecutor):
    extension = 'fs'
    compiler = 'fsc'
    compile_args = ['--nologo', '--out:{exe}', '{source}']


def initialize(sandbox=True):
    # TODO: sandbox is ignored
    if 'fsc' not in env['runtime']:
        return False
    if not os.path.isfile(env['runtime']['fsc']):
        return False
    return test_executor('FS', Executor, 'printfn "Hello, World!"')
