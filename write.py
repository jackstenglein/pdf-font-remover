import sys
import zlib
import platform
import re

#Convert 2 Bytes If Python 3
def C2BIP3(string):
    if sys.version_info[0] > 2:
        if type(string) == bytes:
            return string
        else:
            return bytes([ord(x) for x in string])
    else:
        return string


def FormatOutput(data, raw):
        if raw:
            if type(data) == type([]):
                return ''.join(map(lambda x: x[1], data))
            else:
                return data
        elif sys.version_info[0] > 2:
            return ascii(data)
        else:
            return repr(data)


def SplitByLength(input, length):
    result = []
    while len(input) > length:
        result.append(input[0:length] + '\n')
        input = input[length:]
    result.append(input + '>')
    return result


class Writer:
    def __init__(self, filename, formatFunc):
        """
        __init__ creates all necessary structures to write a PDF. It also creates a blank file with the given filename.
        """
        self.filename = filename
        self.formatFunc = formatFunc
        self.indirectObjects = {}
        fPDF = open(self.filename, 'w')
        fPDF.close()

    def appendBinary(self, str):
        fPDF = open(self.filename, 'ab')
        fPDF.write(C2BIP3(str))
        fPDF.close()
    
    def appendString(self, str):
        fPDF = open(self.filename, 'a')
        fPDF.write(str)
        fPDF.close()

    def filesize(self):
        fPDF = open(self.filename, 'rb')
        fPDF.seek(0, 2)
        size = fPDF.tell()
        fPDF.close()
        return size
        
    def isWindows(self):
        return platform.system() in ('Windows', 'Microsoft')

    def writeComment(self, comment):
        commentStr = repr(comment)
        if not commentStr.startswith('%%EOF'):
            self.appendString(commentStr)

    def writeObject(self, object):
        dataPrecedingStream = object.ContainsStream()
        if dataPrecedingStream:
            compressed = object.Stream(False)
            dictionary = FormatOutput(dataPrecedingStream, True)
            self.writeStream(object.id, object.version, compressed, dictionary)
        else:
            self.writeIndirectObject(object.id, object.version, self.formatFunc(object).strip())

    def writeIndirectObject(self, index, version, io):
        self.appendString("\n")
        self.indirectObjects[index] = self.filesize()
        self.appendString("%d %d obj\n%s\nendobj\n" % (index, version, io))

    def writeStream(self, index, version, streamdata, dictionary):
        self.appendString("\n")
        self.indirectObjects[index] = self.filesize()
        self.appendString(("%d %d obj\n" + dictionary + "\nstream\n") % (index, version))
        self.appendBinary(streamdata)
        self.appendString("\nendstream\nendobj\n")

    def writeXrefAndTrailer(self, rootId, rootVersion, info=None):
        xrefdata = self.writeXref()
        root = ("%d %d R") % (rootId, rootVersion)
        self.writeTrailer(xrefdata[0], xrefdata[1], root, info)

    def writeTrailer(self, startxref, size, root, info=None):
        if info == None:
            self.appendString("trailer\n<<\n /Size %d\n /Root %s\n>>\nstartxref\n%d\n%%%%EOF\n" % (size, root, startxref))
        else:
            self.appendString("trailer\n<<\n /Size %d\n /Root %s\n /Info %s\n>>\nstartxref\n%d\n%%%%EOF\n" % (size, root, info, startxref))

    def writeXref(self):
        self.appendString("\n")
        startxref = self.filesize()
        max = 0
        for i in self.indirectObjects.keys():
            if i > max:
                max = i
        self.appendString("xref\n0 %d\n" % (max+1))
        if self.isWindows():
            eol = '\n'
        else:
            eol = ' \n'
        for i in range(0, max+1):
            if i in self.indirectObjects:
                self.appendString("%010d %05d n%s" % (self.indirectObjects[i], 0, eol))
            else:
                self.appendString("0000000000 65535 f%s" % eol)
        return (startxref, (max+1))
