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

    def __str__(self, indent=0):
        pad_s = ' ' * indent
        child_pad_s = pad_s + ' ' * self.CHILD_INDENT
        attrs_str = '' if not self.attrs else ' {}'.format(' '.join(
            '{}="{}"'.format(k, self.encode_attr_value(v))
            for k, v in self.attrs.items()
        ))
        inner_html = (
            ('\n{}'.format(child_pad_s if self.INDENT_CONTENT else '')
             if self.content else '')
            + (('\n{}'.format(child_pad_s).join(self.content.split('\n')))
               if self.INDENT_CONTENT else self.content)
            + ('\n' if self.children else '')
            + '\n'.join(
                child(indent + self.CHILD_INDENT) for child in self.children
            )
        )
        close_tag = (
            '\n{}</{}>'.format(pad_s, self.TAG_NAME)
            if not self.IS_VOID else ''
        )
        return '{}<{}{}>{}{}'.format(
            pad_s, self.TAG_NAME, attrs_str, inner_html, close_tag
        )

    def __call__(self, indent=0):
        return self.__str__(indent)

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

Document = lambda body_els, head_els=(): (
    '<!DOCTYPE html>\n' + str(
        HTMLElement(
            lang='en',
            children=(
                Head(children=(Meta(charset='utf-8'),) + tuple(head_els)),
                Body(children=body_els)
            )
        )
    )
)
