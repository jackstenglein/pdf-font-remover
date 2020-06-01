
import parser
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


    def UpdatePDF(self, document):
        """pdf-parser, use it to parse a PDF document
        """
        print("Test")


        global decoders


        decoders = []
        runner.LoadDecoders(self.options.decoders, True)

        oPDFParser = parser.Parser(document, self.verbose, self.extract)
        dicObjectTypes = {}

    
        if self.generate:
            savedRoot = ['1', '0', 'R']
            print('#!/usr/bin/python')
            print('')
            print('"""')
            print('')
            print('Program generated by pdf-parser.py by Didier Stevens')
            print('https://DidierStevens.com')
            print('Use at your own risk')
            print('')
            print('Input PDF file: %s' % document)
            print('')
            print('"""')
            print('')
            print('import mPDF')
            print('import sys')
            print('')
            print('def Main():')
            print('    if len(sys.argv) != 2:')
            print("        print('Usage: %s pdf-file' % sys.argv[0])")
            print('        return')
            print('    oPDF = mPDF.cPDF(sys.argv[1])')


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
                # parsing objects inside an /ObjStm object by extracting & parsing the stream content to create a synthesized PDF document, that is then parsed by parser.cPDFParser
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
                oPDFParserOBJSTM = parser.cPDFParser(StringIO(synthesizedPDF), self.options.verbose, self.options.extract, (object.id, object.version))
            
            if object != None:
                if self.options.stats:
                    if object.type == PDF_ELEMENT_COMMENT:
                        cntComment += 1
                    elif object.type == PDF_ELEMENT_XREF:
                        cntXref += 1
                    elif object.type == PDF_ELEMENT_TRAILER:
                        cntTrailer += 1
                    elif object.type == PDF_ELEMENT_STARTXREF:
                        cntStartXref += 1
                    elif object.type == PDF_ELEMENT_INDIRECT_OBJECT:
                        cntIndirectObject += 1
                        type1 = object.GetType()
                        if not type1 in dicObjectTypes:
                            dicObjectTypes[type1] = [object.id]
                        else:
                            dicObjectTypes[type1].append(object.id)
                else:
                    if object.type == PDF_ELEMENT_COMMENT and self.selectComment:
                        if self.options.generate:
                            comment = object.comment[1:].rstrip()
                            if re.match('PDF-\d\.\d', comment):
                                print("    oPDF.header('%s')" % comment[4:])
                            elif comment != '%EOF':
                                print('    oPDF.comment(%s)' % repr(comment))
                        else:
                            print('PDF Comment %s' % runner.FormatOutput(object.comment, self.options.raw))
                            print('')
                    elif object.type == PDF_ELEMENT_XREF and self.selectXref:
                        if not self.options.generate:
                            if self.options.debug:
                                print('xref %s' % runner.FormatOutput(object.content, self.options.raw))
                            else:
                                print('xref')
                            print('')
                    elif object.type == PDF_ELEMENT_TRAILER and self.selectTrailer:
                        oPDFParseDictionary = runner.cPDFParseDictionary(object.content[1:], self.options.nocanonicalizedoutput)
                        if self.options.generate:
                            result = oPDFParseDictionary.Get('/Root')
                            if result != None:
                                savedRoot = result
                        else:
                            if not self.options.search and not self.options.key and not self.options.reference or self.options.search and object.Contains(self.options.search):
                                if oPDFParseDictionary == None:
                                    print('trailer %s' % runner.FormatOutput(object.content, self.options.raw))
                                else:
                                    print('trailer')
                                    oPDFParseDictionary.PrettyPrint('  ')
                                print('')
                            elif self.options.key:
                                if oPDFParseDictionary.parsed != None:
                                    result = oPDFParseDictionary.GetNested(self.options.key)
                                    if result != None:
                                        print(result)
                            elif self.options.reference:
                                for key, value in oPDFParseDictionary.Retrieve():
                                    if value == [str(self.options.reference), '0', 'R']:
                                        print('trailer')
                                        oPDFParseDictionary.PrettyPrint('  ')
                    elif object.type == PDF_ELEMENT_STARTXREF and self.selectStartXref:
                        if not self.options.generate:
                            print('startxref %d' % object.index)
                            print('')
                    elif object.type == PDF_ELEMENT_INDIRECT_OBJECT and self.selectIndirectObject:
                        if self.options.search:
                            if object.Contains(self.options.search):
                                runner.PrintObject(object, self.options)
                        elif self.options.key:
                            contentDictionary = object.ContainsStream()
                            if not contentDictionary:
                                contentDictionary = object.content[1:]
                            oPDFParseDictionary = runner.cPDFParseDictionary(contentDictionary, self.options.nocanonicalizedoutput)
                            if oPDFParseDictionary.parsed != None:
                                result = oPDFParseDictionary.GetNested(self.options.key)
                                if result != None:
                                    print(result)
                        elif self.options.object:
                            if MatchObjectID(object.id, self.options.object):
                                runner.PrintObject(object, self.options)
                        elif self.options.reference:
                            if object.References(self.options.reference):
                                runner.PrintObject(object, self.options)
                        elif self.options.type:
                            if runner.EqualCanonical(object.GetType(), self.optionsType):
                                runner.PrintObject(object, self.options)
                        elif self.options.hash:
                            print('obj %d %d' % (object.id, object.version))
                            rawContent = runner.FormatOutput(object.content, True)
                            print(' len: %d md5: %s' % (len(rawContent), hashlib.md5(rawContent).hexdigest()))
                            print('')
                        elif self.options.searchstream:
                            if object.StreamContains(self.options.searchstream, not self.options.unfiltered, self.options.casesensitive, self.options.regex, self.options.overridingfilters):
                                runner.PrintObject(object, self.options)
                        elif self.options.generateembedded != 0:
                            if object.id == self.options.generateembedded:
                                PrintGenerateObject(object, self.options, 8)
                        else:
                            runner.PrintObject(object, self.options)
                    elif object.type == PDF_ELEMENT_MALFORMED:
                        try:
                            fExtract = open(self.options.extract, 'wb')
                            try:
                                fExtract.write(C2BIP3(object.content))
                            except:
                                print('Error writing file %s' % self.options.extract)
                            fExtract.close()
                        except:
                            print('Error writing file %s' % self.options.extract)
            else:
                break

        if self.options.stats:
            print('Comment: %s' % cntComment)
            print('XREF: %s' % cntXref)
            print('Trailer: %s' % cntTrailer)
            print('StartXref: %s' % cntStartXref)
            print('Indirect object: %s' % cntIndirectObject)
            for key in sorted(dicObjectTypes.keys()):
                print(' %s %d: %s' % (key, len(dicObjectTypes[key]), ', '.join(map(lambda x: '%d' % x, dicObjectTypes[key]))))

        if self.options.generate or self.options.generateembedded != 0:
            print("    oPDF.xrefAndTrailer('%s')" % ' '.join(savedRoot))
            print('')
            print("if __name__ == '__main__':")
            print('    Main()')
