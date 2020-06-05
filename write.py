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
            decompressed = object.Stream()
            # print("Decompressed stream: ", decompressed)

            dictionary = FormatOutput(dataPrecedingStream, True)
            dictionary = re.sub(r'/Length\s+\d+', '', dictionary)
            dictionary = re.sub(r'/Filter\s*/[a-zA-Z0-9]+', '', dictionary)
            dictionary = re.sub(r'/Filter\s*\[.+\]', '', dictionary)
            dictionary = re.sub(r'^\s*<<', '', dictionary)
            dictionary = re.sub(r'>>\s*$', '', dictionary)
            dictionary = dictionary.strip()            
            self.stream2(object.id, object.version, decompressed.rstrip(), dictionary, "f")
        else:
            self.writeIndirectObject(object.id, object.version, self.formatFunc(object).strip())

    def writeIndirectObject(self, index, version, io):
        self.appendString("\n")
        self.indirectObjects[index] = self.filesize()
        self.appendString("%d %d obj\n%s\nendobj\n" % (index, version, io))

    def writeStream(self, index, version, streamdata, dictionary="<< /Length %d >>"):
        self.appendString("\n")
        self.indirectObjects[index] = self.filesize()
        self.appendString(("%d %d obj\n" + dictionary + "\nstream\n") % (index, version, len(streamdata)))
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

#############################################################
        
    def binary(self):
        self.appendString("%\xD0\xD0\xD0\xD0\n")    

    def Data2HexStr(self, data):
        hex = ''
        if sys.version_info[0] == 2:
            for b in data:
                hex += "%02x" % ord(b)
        else:
            for b in data:
                hex += "%02x" % b
        return hex

    def stream2(self, index, version, streamdata, entries="", filters=""):
        """
    * h ASCIIHexDecode
    * H AHx
    * i like ASCIIHexDecode but with 512 long lines
    * I like AHx but with 512 long lines
    * ASCII85Decode
    * LZWDecode
    * f FlateDecode
    * F Fl
    * RunLengthDecode
    * CCITTFaxDecode
    * JBIG2Decode
    * DCTDecode
    * JPXDecode
    * Crypt
        """
        
        encodeddata = streamdata
        filter = []
        for i in filters:
            if i.lower() == "h":
                encodeddata = self.Data2HexStr(encodeddata) + '>'
                if i == "h":
                    filter.insert(0, "/ASCIIHexDecode")
                else:
                    filter.insert(0, "/AHx")
            elif i.lower() == "i":
                encodeddata = ''.join(SplitByLength(self.Data2HexStr(encodeddata), 512))
                if i == "i":
                    filter.insert(0, "/ASCIIHexDecode")
                else:
                    filter.insert(0, "/AHx")
            elif i.lower() == "f":
                encodeddata = zlib.compress(C2BIP3(encodeddata))
                if i == "f":
                    filter.insert(0, "/FlateDecode")
                else:
                    filter.insert(0, "/Fl")
            else:
                print("Error")
                return
        self.appendString("\n")
        self.indirectObjects[index] = self.filesize()
        self.appendString("%d %d obj\n<<\n /Length %d\n" % (index, version, len(encodeddata)))
        if len(filter) == 1:
            self.appendString(" /Filter %s\n" % filter[0])
        if len(filter) > 1:
            self.appendString(" /Filter [%s]\n" % ' '.join(filter))
        if entries != "":
            self.appendString(" %s\n" % entries)
        self.appendString(">>\nstream\n")
        if filters[-1].lower() == 'i':
            self.appendString(encodeddata)
        else:
            self.appendBinary(encodeddata)
        self.appendString("\nendstream\nendobj\n")
