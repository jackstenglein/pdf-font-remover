import optparse
import os
import sys

import destroyer

__description__ = 'fontdestroy makes all fonts in a PDF document non-extractable'
__version__ = '0.1.0'
__minimum_python_version__ = (2, 5, 1)
__maximum_python_version__ = (3, 7, 5)


def GetArguments():
    arguments = sys.argv[1:]
    return arguments

def Main():
    """Main handles reading flags/arguments from the command line, and passes those to the destroyer."""

    oParser = optparse.OptionParser(usage='usage: %prog [options] pdf-file\n' + __description__, version='%prog ' + __version__)
    oParser.add_option('-p', '--print', action='store_true', default=False, help='print each object found in the PDF')
    (options, args) = oParser.parse_args(GetArguments())

    if len(args) != 1:
        oParser.print_help()
        print('')
        print('  %s' % __description__)
        return

    fontDestroyer = destroyer.FontDestroyer(options)
    fontDestroyer.UpdatePDF(args[0])


def TestPythonVersion(enforceMaximumVersion=False, enforceMinimumVersion=False):
    """TestPythonVersion checks that the running version of Python is supported and optionally exits if it is not."""
    if sys.version_info[0:3] > __maximum_python_version__:
        if enforceMaximumVersion:
            print('This program does not work with this version of Python (%d.%d.%d)' % sys.version_info[0:3])
            print('Please use Python version %d.%d.%d' % __maximum_python_version__)
            sys.exit()
        else:
            print('This program has not been tested with this version of Python (%d.%d.%d)' % sys.version_info[0:3])
            print('Should you encounter problems, please use Python version %d.%d.%d' % __maximum_python_version__)
    if sys.version_info[0:3] < __minimum_python_version__:
        if enforceMinimumVersion:
            print('This program does not work with this version of Python (%d.%d.%d)' % sys.version_info[0:3])
            print('Please use Python version %d.%d.%d' % __maximum_python_version__)
            sys.exit()
        else:
            print('This program has not been tested with this version of Python (%d.%d.%d)' % sys.version_info[0:3])
            print('Should you encounter problems, please use Python version %d.%d.%d' % __maximum_python_version__)


if __name__ == '__main__':
    TestPythonVersion()
    Main()
