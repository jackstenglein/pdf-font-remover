
import parser
import write
import pdf_objects
import sys
from io import StringIO
import re

CHAR_WHITESPACE = 1
CHAR_DELIMITER = 2
CHAR_REGULAR = 3

PDF_ELEMENT_COMMENT = 1
PDF_ELEMENT_INDIRECT_OBJECT = 2
PDF_ELEMENT_XREF = 3
PDF_ELEMENT_TRAILER = 4
PDF_ELEMENT_STARTXREF = 5
PDF_ELEMENT_MALFORMED = 6

#Convert 2 String If Python 3
def C2SIP3(bytes):
    if sys.version_info[0] > 2:
        return ''.join([chr(byte) for byte in bytes])
    else:
        return bytes


class FontDestroyer:
    """
    FontDestroyer changes fonts in PDF documents to have a missing ToUnicode table.
    """

    def __init__(self, options={}):
        """
        __init__ constructs the necessary attributes for a new FontDestroyer.
        """
        self.print = options.print

    @staticmethod
    def FormatFont(obj):
        # Add /ToUnicode 524 0 R
        emptyToUnicode = [(CHAR_REGULAR, '/ToUnicode'), (CHAR_WHITESPACE, ' '), (CHAR_REGULAR, '524'), (CHAR_WHITESPACE, ' '), (CHAR_REGULAR, '0'), \
            (CHAR_WHITESPACE, ' '), (CHAR_REGULAR, 'R'), (CHAR_WHITESPACE, ' ')]
        for token in emptyToUnicode:
            obj.content.insert(len(obj.content) - 2, token)

        return FontDestroyer.FormatOutput(obj.content, True)

    @staticmethod
    def FormatObject(obj):
        if obj.GetType() == "/Font":
            return FontDestroyer.FormatFont(obj)
        else:
            return FontDestroyer.FormatOutput(obj.content, True)

    @staticmethod
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

    def UpdatePDF(self, document):
        """pdf-parser, use it to parse a PDF document
        """
        oPDFParser = parser.Parser(document)
        writer = write.Writer("font-output.pdf", FontDestroyer.FormatObject)
        rootId = None
        rootVersion = None

        oPDFParserOBJSTM = None
        while True:
            if oPDFParserOBJSTM == None:
                object = oPDFParser.GetObject()
            else:
                object = oPDFParserOBJSTM.GetObject()
                if object == None:
                    oPDFParserOBJSTM = None
                    object = oPDFParser.GetObject()

            if object == None:
                break
            
            if object.GetType() == '/ObjStm' and object.ContainsStream():
                # parsing objects inside an /ObjStm object by extracting & parsing the stream content to create a synthesized PDF document, that is then itself parsed
                oPDFParseDictionary = pdf_objects.ParseDictionary(object.ContainsStream(), False)
                numberOfObjects = int(oPDFParseDictionary.Get('/N')[0])
                offsetFirstObject = int(oPDFParseDictionary.Get('/First')[0])
                indexes = list(map(int, C2SIP3(object.Stream())[:offsetFirstObject].strip().split(' ')))
                if len(indexes) % 2 != 0 or len(indexes) / 2 != numberOfObjects:
                    raise Exception('Error in index of /ObjStm stream')
                streamObject = C2SIP3(object.Stream()[offsetFirstObject:])
                synthesizedPDF = ''
                while len(indexes) > 0:
                    objectNumber = indexes[0]
                    offset = indexes[1]
                    indexes = indexes[2:]
                    if len(indexes) >= 2:
                        offsetNextObject = indexes[1]
                    else:
                        offsetNextObject = len(streamObject)
                    synthesizedPDF += '%d 0 obj\n%s\nendobj\n' % (objectNumber, streamObject[offset:offsetNextObject])
                oPDFParserOBJSTM = parser.Parser(StringIO(synthesizedPDF), (object.id, object.version))


            # Handle writing to PDF file
            if object.type == PDF_ELEMENT_COMMENT:
                writer.writeComment(object)

            # If we see a trailer object, try to get the root value from it. If that fails for some reason, stick with
            # the root value pulled from the catalog object
            elif object.type == PDF_ELEMENT_TRAILER:
                oPDFParseDictionary = pdf_objects.ParseDictionary(object.content[1:], False)
                result = oPDFParseDictionary.Get('/Root')
                if result != None and len(result) > 1:
                    try:
                        objectId = int(result[0])
                        objectVersion = int(result[1])
                        rootId = objectId
                        rootVersion = objectVersion
                        # print("Got root from trailer")
                    except ValueError:
                        pass
            
            elif object.type == PDF_ELEMENT_INDIRECT_OBJECT:
                writer.writeObject(object)

            # Search for document catalog to use as root reference
            if object.GetType() == "/Catalog":
                # print("Found object catalog: %d %d R" % (object.id, object.version))
                rootId = object.id
                rootVersion = object.version

            if self.print:
                object.Print()
            

        if rootId == None or rootVersion == None:
            print('ERROR: Failed to find document catalog')
            return

        with open('EmptyToUnicode.txt', 'r') as f:
            emptyToUnicode = f.read()
            writer.writeIndirectObject(524, 0, emptyToUnicode)
            
        writer.writeXrefAndTrailer(rootId, rootVersion)
