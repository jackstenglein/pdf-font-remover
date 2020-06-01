import optparse
import os
import sys

import destroyer

__description__ = 'pdf-parser, use it to parse a PDF document'
__version__ = '0.7.4'
__minimum_python_version__ = (2, 5, 1)
__maximum_python_version__ = (3, 7, 5)


def GetArguments():
    arguments = sys.argv[1:]
    envvar = os.getenv('PDFPARSER_OPTIONS')
    if envvar == None:
        return arguments
    return envvar.split(' ') + arguments

def Main():
    """Main handles reading flags/arguments from the command line, and passes those to the runner."""

    oParser = optparse.OptionParser(usage='usage: %prog [options] pdf-file|zip-file|url\n' + __description__, version='%prog ' + __version__)
    oParser.add_option('-s', '--search', help='string to search in indirect objects (except streams)')
    oParser.add_option('-f', '--filter', action='store_true', default=False, help='pass stream object through filters (FlateDecode, ASCIIHexDecode, ASCII85Decode, LZWDecode and RunLengthDecode only)')
    oParser.add_option('-o', '--object', help='id(s) of indirect object(s) to select, use comma (,) to separate ids (version independent)')
    oParser.add_option('-r', '--reference', help='id of indirect object being referenced (version independent)')
    oParser.add_option('-e', '--elements', help='type of elements to select (cxtsi)')
    oParser.add_option('-w', '--raw', action='store_true', default=False, help='raw output for data and filters')
    oParser.add_option('-a', '--stats', action='store_true', default=False, help='display stats for pdf document')
    oParser.add_option('-t', '--type', help='type of indirect object to select')
    oParser.add_option('-O', '--objstm', action='store_true', default=False, help='parse stream of /ObjStm objects')
    oParser.add_option('-v', '--verbose', action='store_true', default=False, help='display malformed PDF elements')
    oParser.add_option('-x', '--extract', help='filename to extract malformed content to')
    oParser.add_option('-H', '--hash', action='store_true', default=False, help='display hash of objects')
    oParser.add_option('-n', '--nocanonicalizedoutput', action='store_true', default=False, help='do not canonicalize the output')
    oParser.add_option('-d', '--dump', help='filename to dump stream content to')
    oParser.add_option('-D', '--debug', action='store_true', default=False, help='display debug info')
    oParser.add_option('-c', '--content', action='store_true', default=False, help='display the content for objects without streams or with streams without filters')
    oParser.add_option('--searchstream', help='string to search in streams')
    oParser.add_option('--unfiltered', action='store_true', default=False, help='search in unfiltered streams')
    oParser.add_option('--casesensitive', action='store_true', default=False, help='case sensitive search in streams')
    oParser.add_option('--regex', action='store_true', default=False, help='use regex to search in streams')
    oParser.add_option('--overridingfilters', type=str, default='', help='override filters with given filters (use raw for the raw stream content)')
    oParser.add_option('-g', '--generate', action='store_true', default=False, help='generate a Python program that creates the parsed PDF file')
    oParser.add_option('--generateembedded', type=int, default=0, help='generate a Python program that embeds the selected indirect object as a file')
    oParser.add_option('--decoders', type=str, default='', help='decoders to load (separate decoders with a comma , ; @file supported)')
    oParser.add_option('--decoderoptions', type=str, default='', help='options for the decoder')
    oParser.add_option('-k', '--key', help='key to search in dictionaries')
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
