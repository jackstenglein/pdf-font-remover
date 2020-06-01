from io import StringIO
import sys
import runner

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

class Document:
    """
    Document provides functions to read bytes from a PDF file.
    """

    def __init__(self, file):
        """
        __init__ opens the given file and creates necessary structures to provide byte reading.
        """

        self.ungetted = []
        if type(file) != str:
            self.infile = file
        else:
            try:
                self.infile = open(file, 'rb')
            except:
                print('Error opening file %s' % file)
                print(sys.exc_info()[1])
                sys.exit()

    def byte(self):
        """
        byte returns a single byte from the PDF file. byte returns None if the file has been completely read.
        """

        if len(self.ungetted) > 0:
            return self.ungetted.pop()

        inbyte = self.infile.read(1)
        if not inbyte or inbyte == '':
            self.infile.close()
            return None

        return ord(inbyte)

    def unget(self, byte):
        """
        unget saves the given byte to be returned in the next call to byte.
        """

        self.ungetted.append(byte)


class Tokenizer:
    """
    Tokenizer tokenizes a PDF file.
    """

    def __init__(self, file):
        """
        __init__ creates data structures needed to tokenize the file.
        """

        self.pdf = Document(file)
        self.ungetted = []
        self.finished = False

    @staticmethod
    def CharacterClass(byte):
        """
        Returns whether the given byte is whitespace, delimiter or normal character.
        """

        if byte == 0 or byte == 9 or byte == 10 or byte == 12 or byte == 13 or byte == 32:
            return CHAR_WHITESPACE
        if byte == 0x28 or byte == 0x29 or byte == 0x3C or byte == 0x3E or byte == 0x5B or byte == 0x5D or byte == 0x7B or byte == 0x7D or byte == 0x2F or byte == 0x25:
            return CHAR_DELIMITER
        return CHAR_REGULAR

    def Token(self):
        """
        Token returns the next token in the PDF file.
        """

        if len(self.ungetted) != 0:
            return self.ungetted.pop()

        if self.finished:
            return None

        byte = self.pdf.byte()
        if byte == None:
            self.finished = True
            return None

        if Tokenizer.CharacterClass(byte) == CHAR_WHITESPACE:
            file_str = StringIO()
            while byte != None and Tokenizer.CharacterClass(byte) == CHAR_WHITESPACE:
                file_str.write(chr(byte))
                byte = self.pdf.byte()
            if byte != None:
                self.pdf.unget(byte)
            else:
                self.finished = True
            self.token = file_str.getvalue()
            return (CHAR_WHITESPACE, self.token)
        elif Tokenizer.CharacterClass(byte) == CHAR_REGULAR:
            file_str = StringIO()
            while byte != None and Tokenizer.CharacterClass(byte) == CHAR_REGULAR:
                file_str.write(chr(byte))
                byte = self.pdf.byte()
            if byte != None:
                self.pdf.unget(byte)
            else:
                self.finished = True
            self.token = file_str.getvalue()
            return (CHAR_REGULAR, self.token)
        else:
            if byte == 0x3C:
                byte = self.pdf.byte()
                if byte == 0x3C:
                    return (CHAR_DELIMITER, '<<')
                else:
                    self.pdf.unget(byte)
                    return (CHAR_DELIMITER, '<')
            elif byte == 0x3E:
                byte = self.pdf.byte()
                if byte == 0x3E:
                    return (CHAR_DELIMITER, '>>')
                else:
                    self.pdf.unget(byte)
                    return (CHAR_DELIMITER, '>')
            elif byte == 0x25:
                file_str = StringIO()
                while byte != None:
                    file_str.write(chr(byte))
                    if byte == 10 or byte == 13:
                        byte = self.pdf.byte()
                        break
                    byte = self.pdf.byte()
                if byte != None:
                    if byte == 10:
                        file_str.write(chr(byte))
                    else:
                        self.pdf.unget(byte)
                else:
                    self.finished = True
                self.token = file_str.getvalue()
                return (CHAR_DELIMITER, self.token)
            return (CHAR_DELIMITER, chr(byte))

    def TokenIgnoreWhiteSpace(self):
        """
        TokenIgnoreWhiteSpace returns the next non-whitespace token in the PDF file.
        """

        token = self.Token()
        while token != None and token[0] == CHAR_WHITESPACE:
            token = self.Token()
        return token

    def Tokens(self):
        """
        Tokens returns a list of all tokens in the PDF file.
        """

        tokens = []
        token = self.Token()
        while token != None:
            tokens.append(token)
            token = self.Token()
        return tokens

    def unget(self, token):
        """
        unget saves the given token to be returned in the next call to Token.
        """
    
        self.ungetted.append(token)


class Parser:
    def __init__(self, file, verbose=False, extract=None, objstm=None):
        self.context = CONTEXT_NONE
        self.content = []
        self.tokenizer = Tokenizer(file)
        self.verbose = verbose
        self.extract = extract
        self.objstm = objstm

    def GetObject(self):
        token = ""
        obj = None

        while (token != None) and (obj == None):
            if self.context == CONTEXT_OBJ:
                token = self.tokenizer.Token()
            else:
                token = self.tokenizer.TokenIgnoreWhiteSpace()

            obj = self.HandleToken(token)
        
        # print("Returning object: ", obj)
        return obj     

    def HandleDelimiter(self, token):
        if token[1][0] == '%':
            if self.context == CONTEXT_OBJ:
                self.content.append(token)
                return None
            return runner.cPDFElementComment(token[1])

        if self.context == CONTEXT_NONE:
            return None
        
        finalToken = token
        if token[1] == '/':
            nextToken = self.tokenizer.Token()
            if nextToken[0] == CHAR_REGULAR:
                finalToken = (CHAR_DELIMITER, token[1] + nextToken[1])
            else:
                self.tokenizer.unget(nextToken)
    
        self.content.append(finalToken)
        return None

    def HandleRegular(self, token):
        if self.context == CONTEXT_OBJ:
            if token[1] == 'endobj':
                self.oPDFElementIndirectObject = runner.cPDFElementIndirectObject(self.objectId, self.objectVersion, self.content, self.objstm)
                self.context = CONTEXT_NONE
                self.content = []
                return self.oPDFElementIndirectObject
            self.content.append(token)
            return None
        
        if self.context == CONTEXT_TRAILER:
            if token[1] == 'startxref' or token[1] == 'xref':
                self.oPDFElementTrailer = runner.cPDFElementTrailer(self.content)
                self.tokenizer.unget(token)
                self.context = CONTEXT_NONE
                self.content = []
                return self.oPDFElementTrailer
            self.content.append(token)
            return None

        if self.context == CONTEXT_XREF:
            if token[1] == 'trailer' or token[1] == 'xref':
                self.oPDFElementXref = runner.cPDFElementXref(self.content)
                self.tokenizer.unget(token)
                self.context = CONTEXT_NONE
                self.content = []
                return self.oPDFElementXref
            self.content.append(token)
            return None

        if runner.IsNumeric(token[1]):
            token2 = self.tokenizer.TokenIgnoreWhiteSpace()
            if runner.IsNumeric(token2[1]):
                token3 = self.tokenizer.TokenIgnoreWhiteSpace()
                if token3[1] == 'obj':
                    self.objectId = int(token[1], 10)
                    self.objectVersion = int(token2[1], 10)
                    self.context = CONTEXT_OBJ
                    return None
                self.tokenizer.unget(token3)
            self.tokenizer.unget(token2)
            return None
        
        if token[1] == 'trailer':
            self.context = CONTEXT_TRAILER
            self.content = [token]
            return None
        
        if token[1] == 'xref':
            self.context = CONTEXT_XREF
            self.content = [token]
            return None

        if token[1] == 'startxref':
            token2 = self.tokenizer.TokenIgnoreWhiteSpace()
            if token2 and runner.IsNumeric(token2[1]):
                return runner.cPDFElementStartxref(int(token2[1], 10))
            self.tokenizer.unget(token2)
            return None
        
        print("Malformed PDF? Token: ", token, " Context: ", self.context)
        return None


    def HandleToken(self, token):
        if token == None:
            return None

        if token[0] == CHAR_DELIMITER:
            return self.HandleDelimiter(token)

        if token[0] == CHAR_WHITESPACE:
            return self.HandleWhitespace(token)

        return self.HandleRegular(token)


    def HandleWhitespace(self, token):
        if self.context != CONTEXT_NONE:
            self.content.append(token)
        return None 
