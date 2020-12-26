"""HTML Document and Element String Generators
"""

class HTMLElement:
    TAG_NAME = 'html'
    IS_VOID = False
    REQUIRED_ATTRS = ()
    INDENT_CONTENT = True
    CHILD_INDENT = 2

    def __init__(self, content='', children=None, **attrs):
        if self.IS_VOID and content:
            raise AssertionError(
                'content not allowed for void tag "{}"'.format(self.TAG_NAME)
            )

        if any(k not in attrs for k in self.REQUIRED_ATTRS):
            raise AssertionError(
                'missing required attrs {} for tag "{}"'.format(
                    [k for k in self.REQUIRED_ATTRS if k not in attrs],
                    tag_name
                )
            )

        self.content = content
        self.attrs = attrs
        self.children = children or []

    @staticmethod
    def encode_attr_value(v):
        return str(v).replace('"', '&quot;')

    def append_child(self, child):
        self.children.append(child)

    @staticmethod
    def _pad_gen(num):
        while num > 0:
            yield ' '
            num -= 1

    def __call__(self, indent=0):
        """Return a character generator.
        """
        # Yield the start tag.
        yield from self._pad_gen(indent)
        yield '<'
        yield from self.TAG_NAME
        if self.attrs:
            for k, v in self.attrs.items():
                yield ' '
                yield from k
                yield '='
                yield '"'
                yield from self.encode_attr_value(v)
                yield '"'
        yield '>'
        yield '\n'

        # Yield the content.
        if self.content:
            if not self.INDENT_CONTENT:
                yield from self.content
            else:
                yield from self._pad_gen(indent + self.CHILD_INDENT)
                for c in self.content:
                    yield c
                    if c == '\n':
                        yield from self._pad_gen(indent + self.CHILD_INDENT)
            yield '\n'

        # Yield the children.
        if self.children:
            for child in self.children:
                yield from child(indent + self.CHILD_INDENT)

        # Maybe yield closing tag.
        if not self.IS_VOID:
            yield from self._pad_gen(indent)
            yield '<'
            yield '/'
            yield from self.TAG_NAME
            yield '>'
            yield '\n'

class VoidHTMLElement(HTMLElement):
    IS_VOID = True

class Head(HTMLElement):
    TAG_NAME = 'head'

class Meta(VoidHTMLElement):
    TAG_NAME = 'meta'

class Body(HTMLElement):
    TAG_NAME = 'body'

class Anchor(HTMLElement):
    TAG_NAME = 'a'

class Span(HTMLElement):
    TAG_NAME = 'span'

class Div(HTMLElement):
    TAG_NAME = 'div'

class Paragraph(HTMLElement):
    TAG_NAME = 'p'

class Button(HTMLElement):
    TAG_NAME = 'button'

class Input(VoidHTMLElement):
    TAG_NAME = 'input'
    REQUIRED_ATTRS = ('type',)

class Form(HTMLElement):
    TAG_NAME = 'form'

class Image(VoidHTMLElement):
    TAG_NAME = 'img'
    REQUIRED_ATTRS = ('src', 'alt')

class Style(HTMLElement):
    TAG_NAME = 'style'

class Script(HTMLElement):
    TAG_NAME = 'script'

class TextArea(HTMLElement):
    TAG_NAME = 'textarea'
    INDENT_CONTENT = False

DOCTYPE = '<!DOCTYPE html>'

def Document(body_els, head_els=()):
    yield from DOCTYPE
    yield '\n'
    yield from HTMLElement(
        lang='en',
        children=(
            Head(children=(Meta(charset='utf-8'),) + tuple(head_els)),
            Body(children=body_els)
        )
    )()

class GenReader:
    """Implement file-like access via readinto() for an HTML generator.
    """
    def __init__(self, gen, encoding='utf-8'):
        self.gen = gen
        self.encoding = encoding

    def readinto(self, buf):
        # Write up to len(buf) bytes into buf from the generator and return the
        # number of bytes written.
        i = 0
        buf_size = len(buf)
        while i < buf_size:
            try:
                char = next(self.gen)
            except StopIteration:
                break
            for byte in char.encode(self.encoding):
                buf[i] = byte
                i += 1
        return i

DocumentStream = lambda *args, **kwargs: GenReader(Document(*args, **kwargs))
