#!/usr/bin/env python
import sys
import subprocess
import os
import time
import signal
import optparse
import datetime
import inspect

VERSION='0.0.1'
ALL_TESTS=[]
LOGFILE='testsuite.log'
CURRENT_SUITE='default'

#See README for detailed info

#Define a test - to be called in the testsuite files

def DefSuite(suite):
    CURRENT_SUITE = suite

def DefTest(cmd, name, success_codes=[0], timeout=30):

    if name in set(t.name for t in ALL_TESTS):
        raise NameError('The test name ''%s'' is already defined' % name)

    frame = inspect.stack()[1]
    cwd = os.path.dirname(inspect.getfile(frame[0])) or './'

    test_location = {'cwd':      cwd,
                     'filename': inspect.getfile(frame[0]),
                     'lineno':   frame[0].f_lineno
                    }
    t = Test(test_location, cmd, name, CURRENT_SUITE, success_codes, timeout)
    ALL_TESTS.append(t)

class SimpleEnum(object):

    def __str__(self):
        return self.__class__.__name__

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __repr__(self):
        return str(self)

class TestResult(object):
    class PASS(SimpleEnum): pass
    class FAIL(SimpleEnum): pass
    class TIMEDOUT(SimpleEnum): pass
    class NOTRUN(SimpleEnum): pass

class TestFailure(object):

    def __init__(self, test, msg):
        self.test_name = test.name
        self.result = test.result
        self.msg = msg

    def __str__(self):
        return '%s %s:\n%s' % (self.result, self.test_name, self.msg)

    def __repr__(self):
        return str(self)

class MultiDelegate(object):

    def __init__(self):
        self.delegates = []

    def __getattr__(self, name):
        def handler(*args, **kwargs):
            for d in self.delegates:
                method = getattr(d, name)
                method(*args, **kwargs)

        return handler
                



class TerminalLog(object):
    GREEN = '\033[92m'
    RED   = '\033[91m'
    ENDC  = '\033[0m'
    
    def __init__(self, out = sys.stdout, verbose=False):
        self.out = out
        self.verbose = verbose
        self.colorize = out.isatty()


    def maybe_color(self, s, color):
        if self.colorize:
            return color + s + self.ENDC
        else:
            return s

    def begin(self):
        self.out.write(
'''## Testsuite started
## Time: %s

''' % (str(datetime.datetime.now())))

    def start_test(self, test):
        self.out.write('  %-70s' % test.name)
        self.out.flush()

    def end_test(self, test):
        if test.result == TestResult.PASS():
            s = self.maybe_color(str(test.result), self.GREEN)
        elif test.result == TestResult.NOTRUN():
            s = str(test.result)
        else:
            s = self.maybe_color(str(test.result), self.RED)

        self.out.write('%s\n' % s)
        if self.verbose:
            for err in test.errors:
                self.out.write('\n%s\n\n' % err)

        self.out.flush()


    def end(self, num_tests, num_failures):
        self.out.write('\n')
        if num_failures:
            self.out.write(self.maybe_color("%d of %d tests failed\n" % 
                                         (num_failures, num_tests), self.RED))
        else:
            self.out.write(self.maybe_color("All %d tests passed\n" % 
                                         num_tests, self.GREEN))
        self.out.flush()


class TextLog(object):
    def __init__(self, logfile_name, verbose = False):
        self.out = open(logfile_name, 'w')
        self.logfile_name = logfile_name
        self.verbose = verbose

    def begin(self):
        self.out.write(
'''## Testsuite started
## Time: %s

''' % (str(datetime.datetime.now())))

    def start_test(self, test):
        self.out.write('\n## Test: %s\n' % test.name)
        self.out.write('## Command: %s\n' % test.cmd)
        pass

    def end_test(self, test):
        self.out.write('## Result: %s\n' % test.result)

        if test.errors:
            self.out.write('## %s failures:\n' % str(test))
        for err in test.errors:
            self.out.write('\n%s\n' % err)


    def end(self, num_tests, num_failures):
        self.out.write('\n')
        if num_failures:
            self.out.write("%d of %d tests failed\n" % (num_failures, num_tests))
        else:
            self.out.write("All %d tests passed\n" % num_tests)

        self.out.close()

class Test(object):

    def __init__(self, location, cmd,  name, suite, success_codes, timeout):
        self.location      = location
        self.cmd           = cmd
        self.name          = name
        self.suite         = suite
        self.success_codes = success_codes
        self.timeout       = timeout
        self.result        = TestResult.NOTRUN()
        self.errors        = []

        self.stdout_run_name = os.path.join(self.cwd,name + '.stdout-actual')
        self.stderr_run_name = os.path.join(self.cwd,name + '.stderr-actual')

        self.stdout_name = os.path.join(self.cwd,name + '.stdout')
        self.stderr_name = os.path.join(self.cwd,name + '.stderr')

        self.stdout_diff_name = os.path.join(self.cwd,name + '.stdout-diff')
        self.stderr_diff_name = os.path.join(self.cwd,name + '.stderr-diff')

    @property
    def cwd(self):
        return self.location['cwd']

    @property
    def filename(self):
        return self.location['filename']

    @property
    def lineno(self):
        return self.location['lineno']

    def __str__(self):
        return "%s at %s:%d" %(self.name,
                             self.filename,
                             self.lineno)

    def run_test(self):
        timedout = False
        with open(self.stdout_run_name, 'wb') as stdout:
            with open(self.stderr_run_name, 'wb') as stderr:
                process= subprocess.Popen(self.cmd, 
                                           shell=True,
                                           stdout=stdout,
                                           stderr=stderr,
                                           cwd=self.cwd
                                           )
                (timedout, exitcode) = wait_process(process, self.timeout)


        self.result = TestResult.PASS()

        if timedout:
            self.result = TestResult.TIMEDOUT()
            self.errors.append(TestFailure(self,'Timed out after %d seconds' % self.timeout))
            self.cleanup()
            return 

        #Now diff the stdout and stderr output
        stdout_name = self.stdout_name
        if not os.path.exists(stdout_name):
            stdout_name = '/dev/null'

        stderr_name = self.stderr_name
        if not os.path.exists(stderr_name):
            stderr_name = '/dev/null'

         
        stdout_diff = diff(stdout_name, self.stdout_run_name, self.stdout_diff_name)
        stderr_diff = diff(stderr_name, self.stderr_run_name, self.stderr_diff_name)


        if self.success_codes and exitcode not in self.success_codes:
            self.result = TestResult.FAIL()
            self.errors.append(TestFailure(self, 
                          'Terminated with unexpected exit code %d' % exitcode))
        if stdout_diff:
            self.result = TestResult.FAIL()
            self.errors.append(TestFailure(self, stdout_diff))

        if stderr_diff:
            self.result = TestResult.FAIL()
            self.errors.append(TestFailure(self, stderr_diff))

        self.cleanup()

    def cleanup(test):
        silentremove(test.stdout_run_name)
        silentremove(test.stderr_run_name)
        silentremove(test.stdout_diff_name)
        silentremove(test.stderr_diff_name)


def diff(orig, new, out):
    cmd = ['diff', '-u', orig, new]
    with open(out, 'w') as stdout:
        exitcode = subprocess.call(cmd, stdout=stdout)
        if exitcode not in [0, 1]: #diff itself failed
            raise RuntimeError('Failed(exitcode=%d: %s ' % 
                            (exitcode, str(cmd)))
    with open(out, 'r') as diff_result:
        return diff_result.read()

def wait_process(process, timeout):
    start = datetime.datetime.now()

    # We do polling for now, until a better approach comes about
    while process.poll() is None:
        time.sleep(0.001)
        now = datetime.datetime.now()
        if (now - start).seconds >= timeout:
            os.kill(process.pid, signal.SIGKILL)
            os.waitpid(process.pid, 0)
            return (True, 0)

    return (False, process.returncode)

def run_tests(log, verbose=False, errexit=False):
    num_tests = 0
    num_failures = 0

    log.begin()

    for test in ALL_TESTS:
        num_tests = num_tests + 1

        log.start_test(test)

        test.run_test()
        if test.errors:
            num_failures = num_failures + 1

        log.end_test(test)

        if test.errors and errexit:
            break


    log.end(num_tests, num_failures)

    return num_tests, num_failures
    
def execpyfile(filename):
    with open(filename) as f:
        exec_globals = {'DefTest': DefTest, 'DefSuite': DefSuite}
        code = compile(f.read(), filename, 'exec')
        exec(code, exec_globals, None)


def silentremove(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

def clean():
    silentremove(LOGFILE)
    for test in ALL_TESTS:
        test.cleanup()

def main():
    parser = optparse.OptionParser(usage='usage: %prog [options] test1 ...', 
                                   version=VERSION)
    parser.add_option('-v', '--verbose',
                      action='store_true', dest='verbose', default=False,
                      help='Verbose output')
    parser.add_option('-x', '--exit_success',
                      action='store_true', dest='exit_success', default=False,
                      help='Always exit with exit code 0. '+
                           'Default exit with 0 if all test succeeds or 1 if '
                           'any test fails')
    parser.add_option('-c', '--clean',
                      action='store_true', dest='clean', default=False,
                      help='Clean any output artifacts left by the tests')
    parser.add_option('-l', '--list',
                      action='store_true', dest='list', default=False,
                      help='describes all the tests')
    parser.add_option('-e', '--errexit',
                      action='store_true', dest='errexit', default=False,
                      help='Stop on the first test that fails')

    (options, args) =  parser.parse_args()
    if not args:
        sys.stdout.write('Error: No test files given\n')
        parser.print_help()
        return 1

    for testfile in args:
        execpyfile(testfile)

    if options.clean:
        clean()
        return 0

    if not ALL_TESTS:
        sys.stdout.write('No test cases defined in any of the definition files:\n' + 
                         '\n'.join(args) + '\n')
        return 1

    log = MultiDelegate()
    log.delegates.append(TextLog(LOGFILE, options.verbose))
    log.delegates.append(TerminalLog(verbose=options.verbose))
    (total, failed) = run_tests(log, errexit=options.errexit)

    if options.exit_success or failed == 0:
        return 0

    return 1
    

if __name__== '__main__':
    sys.exit(main())
