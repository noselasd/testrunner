#!/usr/bin/env python
import sys
import re
import subprocess
import os
import optparse
import datetime
import inspect
import threading
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl

VERSION = '0.0.1'
ALL_TESTS = []
LOGFILE = None
CURRENT_SUITE = 'default'

#See README for detailed info

#Start a new test suite
def DefSuite(suite):
    global CURRENT_SUITE
    CURRENT_SUITE = suite

#Define a test - to be called in the testsuite files
def DefTest(cmd, name, success_codes=None, timeout=30):

    if success_codes is None:
        success_codes = [0]

    if name in set(t.name for t in ALL_TESTS):
        raise NameError('The test name ''%s'' is already defined' % name)

    #Figure out the file and line where the test is defined
    frame = inspect.stack()[1]
    cwd = os.path.dirname(inspect.getfile(frame[0])) or './'
    test_location = {'cwd':      cwd,
                     'filename': inspect.getfile(frame[0]),
                     'lineno':   frame[0].f_lineno
                    }

    t = TestCase(test_location, cmd, name, CURRENT_SUITE, success_codes, timeout)
    ALL_TESTS.append(t)

class SimpleEnum(object):

    def __str__(self):
        return self.__class__.__name__

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def __repr__(self):
        return str(self)

class TestResult(object):
    class PASS(SimpleEnum):
        pass
    class FAIL(SimpleEnum):
        pass
    class TIMEDOUT(SimpleEnum):
        pass
    class NOTRUN(SimpleEnum):
        pass

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

    def __init__(self, out = sys.stdout, verbose=False, show_command=False):
        self.out = out
        self.verbose = verbose
        self.show_command = show_command
        self.colorize = out.isatty()

    def maybe_color(self, s, color):
        if self.colorize:
            return color + s + self.ENDC
        else:
            return s

    def begin(self):
        self.out.write(
'''## Testsuite started
## Invocation: %s
## Time: %s
''' % (' '.join(sys.argv), str(datetime.datetime.now())))

    def start_suite(self, suite):
        self.out.write('\n## Running testsuite: %s\n' % suite)
        self.out.flush()

    def start_test(self, test):

        if self.show_command:
            self.out.write('  Command: %s\n' % test.cmd)
        self.out.write('  %-70s' % test.name)
        self.out.flush()

    def end_test(self, test):
        if test.result == TestResult.PASS():
            msg = self.maybe_color(str(test.result), self.GREEN)
        elif test.result == TestResult.NOTRUN():
           msg = str(test.result)
        else:
           msg = self.maybe_color(str(test.result), self.RED)

        self.out.write('%s\n' % msg)
        if self.verbose:
            # might already shown the command
            if test.errors:
                self.out.write('Failed command: %s\n' % test.cmd)
            for err in test.errors:
                self.out.write('\n%s\n\n' % err)

        self.out.flush()

    def end(self, num_tests, num_failures):
        self.out.write('\n')
        if num_failures:
            self.out.write(self.maybe_color('%d of %d tests failed\n' %
                                         (num_failures, num_tests), self.RED))
        else:
            self.out.write(self.maybe_color('All %d tests passed\n' %
                                         num_tests, self.GREEN))
        if LOGFILE:
            self.out.write('View complete log in the %s file.\n' % (LOGFILE))

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
## Invocation: %s
''' % (str(datetime.datetime.now()), ' '.join(sys.argv)))

    def start_suite(self, suite):
        self.out.write('\n## Running testsuite: %s\n' % suite)
        self.out.flush()

    def start_test(self, test):
        self.out.write('\n## Test: %s\n' % test.name)
        self.out.write('## Command: %s\n' % test.cmd)

    def end_test(self, test):
        duration = timedelta_total_seconds(test.end_time - test.start_time)
        self.out.write('## Duration: %f sec.\n' % duration)
        self.out.write('## Result: %s\n' % test.result)

        if test.errors:
            self.out.write('## %s failures:\n' % str(test))
        for err in test.errors:
            self.out.write('\n%s\n' % err)

        self.out.flush()

    def end(self, num_tests, num_failures):
        self.out.write('\n')
        if num_failures:
            self.out.write('%d of %d tests failed\n' % (num_failures, num_tests))
        else:
            self.out.write('All %d tests passed\n' % num_tests)

        self.out.close()

class XMLLog(object):

    def __init__(self, logfile_name):
        self.out = open(logfile_name, 'w')
        self.logfile_name = logfile_name
        self.xml_doc = XMLGenerator(self.out, 'utf-8')
        self.suite_started = False

    def begin(self):
        self.xml_doc.startDocument()
        self.xml_doc.startElement('testsuites',AttributesImpl({}))
        self.xml_doc.characters('\n')
        self.xml_doc.startElement('invocation',AttributesImpl({}))
        self.xml_doc.characters(' '.join(sys.argv))
        self.xml_doc.endElement('invocation')
        self.xml_doc.characters('\n')

    def start_suite(self, suite):
        if self.suite_started:
            self.xml_doc.endElement('testsuite')
            self.xml_doc.characters('\n')

        self.suite_started = True

        attrs = AttributesImpl({'name': suite})
        self.xml_doc.startElement('testsuite', attrs)
        self.xml_doc.characters('\n')

    def start_test(self, test):
        attrs = AttributesImpl({'name': test.name})
        self.xml_doc.startElement('testcase', attrs)
        self.xml_doc.characters('\n')

    def end_test(self, test):
        duration = timedelta_total_seconds(test.end_time - test.start_time)
        self.xml_doc.startElement('duration',AttributesImpl({}))
        self.xml_doc.characters(str(duration))
        self.xml_doc.endElement('duration')
        self.xml_doc.characters('\n')

        attrs = AttributesImpl({})
        self.xml_doc.startElement('result', attrs)
        self.xml_doc.characters(str(test.result))
        self.xml_doc.endElement('result')
        self.xml_doc.characters('\n')

        if test.errors:
            self.xml_doc.startElement('errors', attrs)
            self.xml_doc.characters('\n')
            for err in test.errors:
                self.xml_doc.startElement('error', attrs)
                self.xml_doc.characters(str(err))
                self.xml_doc.endElement('error')
                self.xml_doc.characters('\n')

            self.xml_doc.endElement('errors')

        self.xml_doc.endElement('testcase')
        self.xml_doc.characters('\n')

    def end(self, num_tests, num_failures):

        if self.suite_started:
            self.xml_doc.endElement('testsuite')
            self.xml_doc.characters('\n')

        attrs = AttributesImpl({'tests': str(num_tests), 
                                'failures': str(num_failures)})
        self.xml_doc.startElement('result', attrs)
        if num_failures:
            self.xml_doc.characters(str(TestResult.FAIL()))
        else:
            self.xml_doc.characters(str(TestResult.PASS()))
        self.xml_doc.endElement('result')

        self.xml_doc.endElement('testsuites')
        self.xml_doc.characters('\n')
        self.xml_doc.endDocument()
        self.out.close()

class TestCase(object):

    def __init__(self, location, cmd,  name, suite, success_codes, timeout):
        self.location      = location
        self.cmd           = cmd
        self.name          = name
        self.suite         = suite
        self.success_codes = success_codes
        self.timeout       = timeout
        self.result        = TestResult.NOTRUN()
        self.errors        = []
        self.start_time    = 0
        self.end_time      = 0

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
        return '%s at %s:%d' %(self.name,
                             self.filename,
                             self.lineno)


    def run_test(self):
        timedout = False

        self.start_time = datetime.datetime.now()
        (timedout, exitcode) = execute_program(self.stdout_run_name,
                                               self.stderr_run_name,
                                               self.cwd,
                                               self.cmd,
                                               self.timeout)
        self.end_time = datetime.datetime.now()

        self.result = TestResult.PASS()

        if timedout:
            self.result = TestResult.TIMEDOUT()
            self.errors.append(TestFailure(self,'Timed out after %d seconds' % self.timeout))
            self.cleanup()
            return

        if self.success_codes and exitcode not in self.success_codes:
            self.result = TestResult.FAIL()
            self.errors.append(TestFailure(self,
                          'Terminated with unexpected exit code %d' % exitcode))

        #Now diff the stdout and stderr output
        stdout_name = self.stdout_name
        if not os.path.exists(stdout_name):
            stdout_name = '/dev/null'

        stderr_name = self.stderr_name
        if not os.path.exists(stderr_name):
            stderr_name = '/dev/null'


        stdout_diff = diff(stdout_name, self.stdout_run_name, self.stdout_diff_name)
        stderr_diff = diff(stderr_name, self.stderr_run_name, self.stderr_diff_name)


        if stdout_diff:
            self.result = TestResult.FAIL()
            self.errors.append(TestFailure(self, stdout_diff))

        if stderr_diff:
            self.result = TestResult.FAIL()
            self.errors.append(TestFailure(self, stderr_diff))

        self.cleanup()

    def generate(self):
        execute_program(self.stdout_name,
                        self.stderr_name,
                        self.cwd,
                        self.cmd,
                        self.timeout)

        if os.path.getsize(self.stdout_name) == 0:
            silentremove(self.stdout_name)
        if os.path.getsize(self.stderr_name) == 0:
            silentremove(self.stderr_name)

    def cleanup(self):
        silentremove(self.stdout_run_name)
        silentremove(self.stderr_run_name)
        silentremove(self.stdout_diff_name)
        silentremove(self.stderr_diff_name)

def execute_program(stdout_name, stderr_name, cwd, cmd, timeout):
    with open(stdout_name, 'wb') as stdout:
        with open(stderr_name, 'wb') as stderr:
            process= subprocess.Popen(cmd,
                    shell=True,
                    stdout=stdout,
                    stderr=stderr,
                    cwd=cwd
                    )
            return wait_process(process, timeout)

def wait_process(proc, timeout):
    proc_thread = threading.Thread(target=proc.communicate)
    proc_thread.setDaemon(True)
    proc_thread.start()
    proc_thread.join(timeout=timeout)

    if proc_thread.is_alive():
        try:
            proc.kill()
            return (True, -1)

        except OSError:
            #This takes care of most of the races between
            #is_alive and kill. Though they don't matter much
            #for our cases where the timeout should just be a guard
            pass

    return (False, proc.returncode)

def diff(orig, new, out):
    cmd = ['diff', '-u', orig, new]
    with open(out, 'w') as stdout:
        exitcode = subprocess.call(cmd, stdout=stdout, stderr=stdout)
        if exitcode not in [0, 1]: #diff itself failed
            raise RuntimeError('Failed(exitcode=%d: %s ' %
                            (exitcode, str(cmd)))
    with open(out, 'r') as diff_result:
        return diff_result.read()

def run_tests(log, verbose=False, errexit=False):
    num_tests = 0
    num_failures = 0
    current_suite = None

    log.begin()

    for test in ALL_TESTS:
        num_tests += 1

        if test.suite != current_suite:
            log.start_suite(test.suite)
            current_suite = test.suite

        log.start_test(test)

        test.run_test()
        if test.errors:
            num_failures += 1

        log.end_test(test)

        if test.errors and errexit:
            break


    log.end(num_tests, num_failures)

    return num_tests, num_failures

def generate_test_files(errexit=False):

    num_failures = 0
    for test in ALL_TESTS:
        sys.stdout.write('Regenerating %s with command: %s\n' % (test.name,
                                                               test.cmd))
        try:
            test.generate()
        except Exception as ex:
            sys.stdout.write('%s failed: %s\n' % (test.name, str(ex)))
            num_failures += 1

        if num_failures > 0 and errexit:
            break

    return num_failures == 0

def timedelta_total_seconds(t):
	"""Total seconds in the duration.
Needed since timedelta.total_seconds() doesn't exist in Python 2.6"""
        return ((t.days * 86400.0 + t.seconds)*10.0**6 + t.microseconds) / 10.0**6 

def execpyfile(filename, defines):
    with open(filename) as f:
        exec_globals = defines.copy()
        exec_globals.update({'DefTest': DefTest, 'DefSuite': DefSuite})
        exec_globals.update(defines)
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

def list_tests():
    if ALL_TESTS:
        sys.stdout.write('Available tests:\n')
        l = max([len(t.suite) for t in ALL_TESTS]) + 1

        sys.stdout.write('%-*s Name\n' % (l, 'Suite'))
        sys.stdout.write('%s\n' % ('-' * (l + 5)))

        for test in ALL_TESTS:
            sys.stdout.write('%-*s %s\n' % (l, test.suite, test.name))
        sys.stdout.flush()
    else:
        sys.stdout.write('No tests found\n')

def filter_tests(keywords, getter):
    global ALL_TESTS

    filtered_tests = []
    for include in keywords:
        r = re.compile(include)
        filtered_tests += [t for t in ALL_TESTS if r.search(getter(t))]

    ALL_TESTS = filtered_tests

def parse_defines(defines):
    defines_dict = {}
    for d in defines:
        (var, sep, value) = d.partition('=') 
        if not sep:
            sys.stdout.write("Error define '%s' is not on the form name=value\n" % d)
            sys.exit(1)
        defines_dict[var] = value

    return defines_dict

def main():
    parser = optparse.OptionParser(usage='usage: %prog [options] test1 ...',
                                   version=VERSION)
    parser.add_option('-v', '--verbose',
                      action='store_true', dest='verbose', default=False,
                      help='Verbose output, shows diffs on failed testcases')
    parser.add_option('-C', '--show-command',
                      action='store_true', dest='show_command', default=False,
                      help='Show the command being run for each test.')
    parser.add_option('-x', '--exit_success',
                      action='store_true', dest='exit_success', default=False,
                      help='Always exit with exit code 0. '+
                           'Default exit with 0 if all test succeeds or 1 if '
                           'any test fails')
    parser.add_option('-c', '--clean',
                      action='store_true', dest='clean', default=False,
                      help='Clean any output artifacts left by the tests')
    parser.add_option('-l', '--list',
                      action='store_true', dest='list_tests', default=False,
                      help='List all the test cases')
    parser.add_option('-e', '--errexit',
                      action='store_true', dest='errexit', default=False,
                      help='Stop on the first test that fails')
    parser.add_option('-f', '--logfile',
                      action='store', dest='logfile',
                      help='Name of the output log file')
    parser.add_option('-k', '--keyword',
                      action='append', dest='keyword', default=[],
                      help='Run only tests matching the given keyword. ' +
                           'KEYWORD is a regexp. Can be given multiple times.')
    parser.add_option('-s', '--suite',
                      action='append', dest='suite', default=[],
                      help='Run only test suites matching the given suite. ' +
                           'SUITE is a regexp. Can be given multiple times.')
    parser.add_option('--xml',
                      action='store_true', dest='xml', default=False,
                      help='Write the logfile in XML format')
    parser.add_option('-D', '--define',
                      action='append', dest='define', default=[],
                      help='Define a variable available to the  test files.' +
                           'The variable is defined with the form name=value.' +
                           'Can be given multiple times')
    parser.add_option('-g', '--generate',
                      action='store_true', dest='generate', default=False,
                      help='Run the defined test case commands and generate ' +
                            'the output files. Use with care, this overwrites ' +
                            'existing output files')

    (options, args) =  parser.parse_args()
    if not args:
        sys.stdout.write('Error: No test files given\n')
        parser.print_help()
        return 1

    global LOGFILE
    if options.logfile:
        LOGFILE = options.logfile
    elif options.xml:
        LOGFILE='testsuite.xml'
    else:
        LOGFILE='testsuite.log'

    defines = parse_defines(options.define)
    for testfile in args:
        execpyfile(testfile, defines)

    if options.keyword:
        filter_tests(options.keyword, lambda t: t.name)

    if options.suite:
        filter_tests(options.suite, lambda t: t.suite)

    if options.clean:
        clean()
        return 0

    if options.list_tests:
        list_tests()
        return 0

    if not ALL_TESTS:
        sys.stdout.write('No test cases defined in any of the definition files:\n' +
                         '\n'.join(args) + '\n')
        return 1

    ok = False
    if options.generate:
        ok = generate_test_files(errexit=options.errexit)
    else:
        log = MultiDelegate()
        if options.xml:
            log.delegates.append(XMLLog(LOGFILE))
        else:
            log.delegates.append(TextLog(LOGFILE, options.verbose))

        log.delegates.append(TerminalLog(verbose=options.verbose, 
                                         show_command=options.show_command))
        (total, failed) = run_tests(log, errexit=options.errexit)
        ok = failed == 0

    if options.exit_success or ok:
        return 0

    return 1


if __name__== '__main__':
    sys.exit(main())
