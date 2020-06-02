PDF_ELEMENT_COMMENT = 1
PDF_ELEMENT_INDIRECT_OBJECT = 2
PDF_ELEMENT_XREF = 3
PDF_ELEMENT_TRAILER = 4
PDF_ELEMENT_STARTXREF = 5
PDF_ELEMENT_MALFORMED = 6

class Comment:
    def __init__(self, comment):
        self.type = PDF_ELEMENT_COMMENT
        self.comment = comment

    def __repr__(self):
        return self.comment



class Startxref:
    def __init__(self, index):
        self.type = PDF_ELEMENT_STARTXREF
        self.index = index



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

class Xref:
    def __init__(self, content):
        self.type = PDF_ELEMENT_XREF
        self.content = content
