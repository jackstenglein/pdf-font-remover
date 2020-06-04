
import parser
import write
import runner
from io import StringIO
import re

CHAR_WHITESPACE = 1
CHAR_DELIMITER = 2
CHAR_REGULAR = 3

CONTEXT_NONE = 1
CONTEXT_OBJ = 2
CONTEXT_XREF = 3
CONTEXT_TRAILER = 4

PDF_ELEMENT_COMMENT = 1
PDF_ELEMENT_INDIRECT_OBJECT = 2
PDF_ELEMENT_XREF = 3
PDF_ELEMENT_TRAILER = 4
PDF_ELEMENT_STARTXREF = 5
PDF_ELEMENT_MALFORMED = 6

class FontDestroyer:
    """
    FontDestroyer changes fonts in PDF documents to have a missing ToUnicode table.
    """

    def __init__(self, options={}):
        """
        __init__ constructs the necessary attributes for a new FontDestroyer.
        """
        self.options = options

        self.countComment = 0
        self.countXref = 0
        self.countTrailer = 0
        self.countStartXref = 0
        self.countIndirectObject = 0

        self.verbose = self.options.verbose
        self.extract = self.options.extract
        self.generate = self.options.generate

        if self.options.type == '-':
            self.optionsType = ''
        else:
            self.optionsType = self.options.type

        if self.options.elements:
            self.selectComment = ('c' in elements)
            self.selectXref = ('x' in elements)
            self.selectTrailer = ('t' in elements)
            self.selectStartXref = ('s' in elements)
            self.selectIndirectObject = ('i' in elements)
        else:
            self.selectIndirectObject = True
            if not self.options.search and not self.options.object and not self.options.reference and not self.options.type and not self.options.searchstream and not self.options.key:
                self.selectComment = True
                self.selectXref = True
                self.selectTrailer = True
                self.selectStartXref = True
            if self.options.search or self.options.key or self.options.reference:
                self.selectTrailer = True

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
        if runner.EqualCanonical(obj.GetType(), "/Font"):
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
        oPDFParser = parser.Parser(document, self.verbose, self.extract)
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
                
            
            if self.options.objstm and hasattr(object, 'GetType') and runner.EqualCanonical(object.GetType(), '/ObjStm') and object.ContainsStream():
                # parsing objects inside an /ObjStm object by extracting & parsing the stream content to create a synthesized PDF document, that is then itself parsed
                oPDFParseDictionary = runner.cPDFParseDictionary(object.ContainsStream(), self.options.nocanonicalizedoutput)
                numberOfObjects = int(oPDFParseDictionary.Get('/N')[0])
                offsetFirstObject = int(oPDFParseDictionary.Get('/First')[0])
                indexes = list(map(int, runner.C2SIP3(object.Stream())[:offsetFirstObject].strip().split(' ')))
                if len(indexes) % 2 != 0 or len(indexes) / 2 != numberOfObjects:
                    raise Exception('Error in index of /ObjStm stream')
                streamObject = runner.C2SIP3(object.Stream()[offsetFirstObject:])
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
                oPDFParserOBJSTM = parser.Parser(StringIO(synthesizedPDF), self.options.verbose, self.options.extract, (object.id, object.version))

            if object == None:
                break

            # Handle writing to PDF file
            if object.type == PDF_ELEMENT_COMMENT:
                writer.writeComment(object)

            # If we see a trailer object, try to get the root value from it. If that fails for some reason, stick with
            # the root value pulled from the catalog object
            elif object.type == PDF_ELEMENT_TRAILER:
                oPDFParseDictionary = runner.cPDFParseDictionary(object.content[1:], self.options.nocanonicalizedoutput)
                result = oPDFParseDictionary.Get('/Root')
                if result != None and len(result) > 1:
                    try:
                        objectId = int(result[0])
                        objectVersion = int(result[1])
                        rootId = objectId
                        rootVersion = objectVersion
                        print("Got root from trailer")
                    except ValueError:
                        pass
            
            elif object.type == PDF_ELEMENT_INDIRECT_OBJECT:
                writer.writeObject(object)

            # Search for document catalog to use as root reference
            if runner.EqualCanonical(object.GetType(), "/Catalog"):
                print("Found object catalog: %d %d R" % (object.id, object.version))
                rootId = object.id
                rootVersion = object.version

            # Handle printing to console
            # if object.type == PDF_ELEMENT_COMMENT:
            #     print('PDF Comment %s' % runner.FormatOutput(object.comment, self.options.raw))
            #     print('')

            # elif object.type == PDF_ELEMENT_XREF:
            #     print('xref %s' % runner.FormatOutput(object.content, self.options.raw))
            #     print('')

            # elif object.type == PDF_ELEMENT_TRAILER:
            #     oPDFParseDictionary = runner.cPDFParseDictionary(object.content[1:], self.options.nocanonicalizedoutput)
            #     if oPDFParseDictionary == None:
            #         print('trailer %s' % runner.FormatOutput(object.content, self.options.raw))
            #     else:
            #         print('trailer')
            #         oPDFParseDictionary.PrettyPrint('  ')
            #     print('')
                    
            # elif object.type == PDF_ELEMENT_STARTXREF:
            #     print('startxref %d' % object.index)
            #     print('')

            # elif object.type == PDF_ELEMENT_INDIRECT_OBJECT:
            #     runner.PrintObject(object, self.options)
            



        if rootId == None or rootVersion == None:
            print('ERROR: Failed to find document catalog')
            return

        with open('EmptyToUnicode.txt', 'r') as f:
            emptyToUnicode = f.read()
            writer.writeIndirectObject(524, 0, emptyToUnicode)
            


        writer.writeXrefAndTrailer(rootId, rootVersion)

        # if self.options.generate or self.options.generateembedded != 0:
        #     print("    oPDF.xrefAndTrailer('%s')" % ' '.join(savedRoot))
        #     print('')
        #     print("if __name__ == '__main__':")
        #     print('    Main()')
