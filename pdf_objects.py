import decode
import sys
import re
import zlib

PDF_ELEMENT_COMMENT = 1
PDF_ELEMENT_INDIRECT_OBJECT = 2
PDF_ELEMENT_XREF = 3
PDF_ELEMENT_TRAILER = 4
PDF_ELEMENT_STARTXREF = 5
PDF_ELEMENT_MALFORMED = 6

CHAR_WHITESPACE = 1
CHAR_DELIMITER = 2
CHAR_REGULAR = 3

def Canonicalize(sIn):
    if sIn == '':
        return sIn
    elif sIn[0] != '/':
        return sIn
    elif sIn.find('#') == -1:
        return sIn
    else:
        i = 0
        iLen = len(sIn)
        sCanonical = ''
        while i < iLen:
            if sIn[i] == '#' and i < iLen - 2:
                try:
                    sCanonical += chr(int(sIn[i+1:i+3], 16))
                    i += 2
                except:
                    sCanonical += sIn[i]
            else:
                sCanonical += sIn[i]
            i += 1
        return sCanonical


def CopyWithoutWhiteSpace(content):
    result = []
    for token in content:
        if token[0] != CHAR_WHITESPACE:
            result.append(token)
    return result


def FormatOutput(data):
    if sys.version_info[0] > 2:
        return ascii(data)
    else:
        return repr(data)


def IsNumeric(str):
    return re.match('^[0-9]+', str)


def TrimLWhiteSpace(data):
    while data != [] and data[0][0] == CHAR_WHITESPACE:
        data = data[1:]
    return data


def TrimRWhiteSpace(data):
    while data != [] and data[-1][0] == CHAR_WHITESPACE:
        data = data[:-1]
    return data


class Comment:
    def __init__(self, comment):
        self.type = PDF_ELEMENT_COMMENT
        self.comment = comment

    def __repr__(self):
        return self.comment

    def GetType(self):
        return 'Comment'
    
    def Print(self):
        print('PDF Comment %s' % FormatOutput(self.comment))
        print('')


class Startxref:
    def __init__(self, index):
        self.type = PDF_ELEMENT_STARTXREF
        self.index = index

    def GetType(self):
        return 'Startxref'

    def Print(self):
        print('startxref %d' % self.index)
        print('') 


class Trailer:
    def __init__(self, content):
        self.type = PDF_ELEMENT_TRAILER
        self.content = content

    def Contains(self, keyword):
        data = ''
        for i in range(0, len(self.content)):
            if self.content[i][1] == 'stream':
                break
            else:
                data += Canonicalize(self.content[i][1])
        return data.upper().find(keyword.upper()) != -1

    def GetType(self):
        return 'Trailer'

    def Print(self):
        oPDFParseDictionary = ParseDictionary(self.content[1:], False)
        if oPDFParseDictionary == None:
            print('trailer %s' % FormatOutput(object.content))
        else:
            print('trailer')
            oPDFParseDictionary.PrettyPrint('  ')
        print('')


class Xref:
    def __init__(self, content):
        self.type = PDF_ELEMENT_XREF
        self.content = content

    def GetType(self):
        return 'Xref'

    def Print(self):
        print('xref %s' % FormatOutput(self.content))
        print('')


class IndirectObject:
    def __init__(self, id, version, content, objstm=None):
        self.type = PDF_ELEMENT_INDIRECT_OBJECT
        self.id = id
        self.version = version
        self.content = content
        self.objstm = objstm
        #fix stream for Ghostscript bug reported by Kurt
        if self.ContainsStream():
            position = len(self.content) - 1
            if position < 0:
                return
            while self.content[position][0] == CHAR_WHITESPACE and position >= 0:
                position -= 1
            if position < 0:
                return
            if self.content[position][0] != CHAR_REGULAR:
                return
            if self.content[position][1] == 'endstream':
                return
            if not self.content[position][1].endswith('endstream'):
                return
            self.content = self.content[0:position] + [(self.content[position][0], self.content[position][1][:-len('endstream')])] + [(self.content[position][0], 'endstream')] + self.content[position+1:]

    def GetType(self):
        content = CopyWithoutWhiteSpace(self.content)
        dictionary = 0
        result = ''
        for i in range(0, len(content)):
            if content[i][0] == CHAR_DELIMITER and content[i][1] == '<<':
                dictionary += 1
            if content[i][0] == CHAR_DELIMITER and content[i][1] == '>>':
                dictionary -= 1
            if dictionary == 1 and content[i][0] == CHAR_DELIMITER and Canonicalize(content[i][1]) == '/Type' and i < len(content) - 1:
                result = content[i+1][1]
                break
        return Canonicalize(result)

    def GetReferences(self):
        content = CopyWithoutWhiteSpace(self.content)
        references = []
        for i in range(0, len(content)):
            if i > 1 and content[i][0] == CHAR_REGULAR and content[i][1] == 'R' and content[i-2][0] == CHAR_REGULAR and IsNumeric(content[i-2][1]) and content[i-1][0] == CHAR_REGULAR and IsNumeric(content[i-1][1]):
                references.append((content[i-2][1], content[i-1][1], content[i][1]))
        return references

    def References(self, index):
        for ref in self.GetReferences():
            if ref[0] == index:
                return True
        return False

    def ContainsStream(self):
        for i in range(0, len(self.content)):
            if self.content[i][0] == CHAR_REGULAR and self.content[i][1] == 'stream':
                return self.content[0:i]
        return False

    def Contains(self, keyword):
        data = ''
        for i in range(0, len(self.content)):
            if self.content[i][1] == 'stream':
                break
            else:
                data += Canonicalize(self.content[i][1])
        return data.upper().find(keyword.upper()) != -1

    def ContainsName(self, keyword):
        for token in self.content:
            if token[1] == 'stream':
                return False
            if token[0] == CHAR_DELIMITER and Canonicalize(token[1]) == keyword:
                return True
        return False

    def StreamContains(self, keyword, filter, casesensitive, regex, overridingfilters):
        if not self.ContainsStream():
            return False
        streamData = self.Stream(filter, overridingfilters)
        if filter and streamData == 'No filters':
            streamData = self.Stream(False, overridingfilters)
        if regex:
            return re.search(keyword, streamData, IIf(casesensitive, 0, re.I))
        elif casesensitive:
            return keyword in streamData
        else:
            return keyword.lower() in streamData.lower()

    def Stream(self, filter=True, overridingfilters=''):
        state = 'start'
        countDirectories = 0
        data = ''
        filters = []
        for i in range(0, len(self.content)):
            if state == 'start':
                if self.content[i][0] == CHAR_DELIMITER and self.content[i][1] == '<<':
                    countDirectories += 1
                if self.content[i][0] == CHAR_DELIMITER and self.content[i][1] == '>>':
                    countDirectories -= 1
                if countDirectories == 1 and self.content[i][0] == CHAR_DELIMITER and Canonicalize(self.content[i][1]) == '/Filter':
                    state = 'filter'
                elif countDirectories == 0 and self.content[i][0] == CHAR_REGULAR and self.content[i][1] == 'stream':
                    state = 'stream-whitespace'
            elif state == 'filter':
                if self.content[i][0] == CHAR_DELIMITER and self.content[i][1][0] == '/':
                    filters = [self.content[i][1]]
                    state = 'search-stream'
                elif self.content[i][0] == CHAR_DELIMITER and self.content[i][1] == '[':
                    state = 'filter-list'
            elif state == 'filter-list':
                if self.content[i][0] == CHAR_DELIMITER and self.content[i][1][0] == '/':
                    filters.append(self.content[i][1])
                elif self.content[i][0] == CHAR_DELIMITER and self.content[i][1] == ']':
                    state = 'search-stream'
            elif state == 'search-stream':
                if self.content[i][0] == CHAR_REGULAR and self.content[i][1] == 'stream':
                    state = 'stream-whitespace'
            elif state == 'stream-whitespace':
                if self.content[i][0] == CHAR_WHITESPACE:
                    whitespace = self.content[i][1]
                    if whitespace.startswith('\x0D\x0A') and len(whitespace) > 2:
                        data += whitespace[2:]
                    elif whitespace.startswith('\x0A') and len(whitespace) > 1:
                        data += whitespace[1:]
                else:
                    data += self.content[i][1]
                state = 'stream-concat'
            elif state == 'stream-concat':
                if 'endstream' in self.content[i][1]:
                    index = self.content[i][1].index('endstream')
                    data += self.content[i][1][:index]

                    if filter:
                        if overridingfilters == '':
                            return self.Decompress(data, filters)
                        elif overridingfilters == 'raw':
                            return data
                        else:
                            return self.Decompress(data, overridingfilters.split(' '))
                    else:
                        return data
                else:
                    data += self.content[i][1]
            else:
                return 'Unexpected filter state'
        return filters

    def Decompress(self, data, filters):
        for filter in filters:
            cFilter = Canonicalize(filter)
            if cFilter == '/FlateDecode' or cFilter == '/Fl':
                try:
                    data = decode.FlateDecode(data)
                except zlib.error as e:
                    message = 'FlateDecode decompress failed'
                    if len(data) > 0 and ord(data[0]) & 0x0F != 8:
                        message += ', unexpected compression method: %02x' % ord(data[0])
                    return message + '. zlib.error %s' % e.message
            elif cFilter == '/ASCIIHexDecode' or cFilter == '/AHx':
                try:
                    data = decode.ASCIIHexDecode(data)
                except:
                    return 'ASCIIHexDecode decompress failed'
            elif cFilter == '/ASCII85Decode' or cFilter == '/A85':
                try:
                    data = decode.ASCII85Decode(data.rstrip('>'))
                except:
                    return 'ASCII85Decode decompress failed'
            elif cFilter == '/LZWDecode' or cFilter == '/LZW':
                try:
                    data = decode.LZWDecode(data)
                except:
                    return 'LZWDecode decompress failed'
            elif cFilter == '/RunLengthDecode' or cFilter == '/R':
                try:
                    data = decode.RunLengthDecode(data)
                except:
                    return 'RunLengthDecode decompress failed'
            # elif i.startswith('/CC')                        # CCITTFaxDecode
            # elif i.startswith('/DCT')                       # DCTDecode
            else:
                return 'Unsupported filter: %s' % repr(filters)
        if len(filters) == 0:
            return 'No filters'
        else:
            return data

    def Print(self):
        print('obj %d %d' % (self.id, self.version))
        if self.objstm != None:
            print(' Containing /ObjStm: %d %d' % self.objstm)
        print(' Type: %s' % Canonicalize(self.GetType()))
        print(' Referencing: %s' % ', '.join(map(lambda x: '%s %s %s' % x, self.GetReferences())))
        dataPrecedingStream = self.ContainsStream()
        oPDFParseDictionary = None
        if dataPrecedingStream:
            print(' Contains stream')
            oPDFParseDictionary = ParseDictionary(dataPrecedingStream, False)
        else:
            oPDFParseDictionary = ParseDictionary(self.content, False)
        print('')
        oPDFParseDictionary.PrettyPrint('  ')
        print('')


class ParseDictionary:
    def __init__(self, content, nocanonicalizedoutput):
        self.content = content
        self.nocanonicalizedoutput = nocanonicalizedoutput
        dataTrimmed = TrimLWhiteSpace(TrimRWhiteSpace(self.content))
        if dataTrimmed == []:
            self.parsed = None
        elif self.isOpenDictionary(dataTrimmed[0]) and (self.isCloseDictionary(dataTrimmed[-1]) or self.couldBeCloseDictionary(dataTrimmed[-1])):
            self.parsed = self.ParseDictionary(dataTrimmed)[0]
        else:
            self.parsed = None
        # print("self.parsed: ", self.parsed)

    def isOpenDictionary(self, token):
        return token[0] == CHAR_DELIMITER and token[1] == '<<'

    def isCloseDictionary(self, token):
        return token[0] == CHAR_DELIMITER and token[1] == '>>'

    def couldBeCloseDictionary(self, token):
        return token[0] == CHAR_DELIMITER and token[1].rstrip().endswith('>>')

    def ParseDictionary(self, tokens):
        state = 0 # start
        dictionary = []
        while tokens != []:
            if state == 0:
                if self.isOpenDictionary(tokens[0]):
                    state = 1
                else:
                    return None, tokens
            elif state == 1:
                if self.isOpenDictionary(tokens[0]):
                    pass
                elif self.isCloseDictionary(tokens[0]):
                    return dictionary, tokens
                elif tokens[0][0] != CHAR_WHITESPACE:
                    key = Canonicalize(tokens[0][1])
                    value = []
                    state = 2
            elif state == 2:
                if self.isOpenDictionary(tokens[0]):
                    value, tokens = self.ParseDictionary(tokens)
                    dictionary.append((key, value))
                    state = 1
                elif self.isCloseDictionary(tokens[0]):
                    dictionary.append((key, value))
                    return dictionary, tokens
                elif value == [] and tokens[0][0] == CHAR_WHITESPACE:
                    pass
                elif value == [] and tokens[0][1] == '[':
                    value.append(tokens[0][1])
                elif value != [] and value[0] == '[' and tokens[0][1] != ']':
                    value.append(tokens[0][1])
                elif value != [] and value[0] == '[' and tokens[0][1] == ']':
                    value.append(tokens[0][1])
                    dictionary.append((key, value))
                    value = []
                    state = 1
                elif value == [] and tokens[0][1] == '(':
                    value.append(tokens[0][1])
                elif value != [] and value[0] == '(' and tokens[0][1] != ')':
                    if tokens[0][1][0] == '%':
                        tokens = [tokens[0]] + parser.Tokenizer(StringIO(tokens[0][1][1:])).Tokens() + tokens[1:]
                        value.append('%')
                    else:
                        value.append(tokens[0][1])
                elif value != [] and value[0] == '(' and tokens[0][1] == ')':
                    value.append(tokens[0][1])
                    balanced = 0
                    for item in value:
                        if item == '(':
                            balanced += 1
                        elif item == ')':
                            balanced -= 1
                    if balanced < 0 and self.verbose:
                        print('todo 11: ' + repr(value))
                    if balanced < 1:
                        dictionary.append((key, value))
                        value = []
                        state = 1
                elif value != [] and tokens[0][1][0] == '/':
                    dictionary.append((key, value))
                    key = Canonicalize(tokens[0][1])
                    value = []
                    state = 2
                else:
                    value.append(Canonicalize(tokens[0][1]))
            tokens = tokens[1:]

    def Retrieve(self):
        return self.parsed

    def PrettyPrintSubElement(self, prefix, e):
        if e[1] == []:
            print('%s  %s' % (prefix, e[0]))
        elif type(e[1][0]) == type(''):
            if len(e[1]) == 3 and IsNumeric(e[1][0]) and e[1][1] == '0' and e[1][2] == 'R':
                joiner = ' '
            else:
                joiner = ''
            value = joiner.join(e[1]).strip()
            reprValue = repr(value)
            if "'" + value + "'" != reprValue:
                value = reprValue
            print('%s  %s %s' % (prefix, e[0], value))
        else:
            print('%s  %s' % (prefix, e[0]))
            self.PrettyPrintSub(prefix + '    ', e[1])

    def PrettyPrintSub(self, prefix, dictionary):
        if dictionary != None:
            print('%s<<' % prefix)
            for e in dictionary:
                self.PrettyPrintSubElement(prefix, e)
            print('%s>>' % prefix)

    def PrettyPrint(self, prefix):
        self.PrettyPrintSub(prefix, self.parsed)

    def Get(self, select):
        for key, value in self.parsed:
            if key == select:
                return value
        return None

    def GetNestedSub(self, dictionary, select):
        for key, value in dictionary:
            if key == select:
                return self.PrettyPrintSubElement('', [select, value])
            if type(value) == type([]) and len(value) > 0 and type(value[0]) == type((None,)):
                result = self.GetNestedSub(value, select)
                if result !=None:
                    return self.PrettyPrintSubElement('', [select, result])
        return None

    def GetNested(self, select):
        return self.GetNestedSub(self.parsed, select)
