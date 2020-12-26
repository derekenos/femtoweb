
import os
from os import path

###############################################################################
# Element Helpers
###############################################################################

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

###############################################################################
# Base Document Template
###############################################################################

HTMLDocument = lambda body_els, head_els=(): (
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

###############################################################################
# Text File Editor
###############################################################################

def TextFileEditor(req_path, text):
    filename = path.split(req_path)[-1]
    script = Script(
"""
document.addEventListener('DOMContentLoaded', () => {{
  const inputEl = document.getElementById('textarea')
  const buttonEl = document.getElementById('submit')

  function submit () {{
    fetch(new URL("/_fs/{req_path}", window.location.href), {{
      method: 'PUT',
      headers: {{
        'Content-Type': 'text/plain',
      }},
      redirect: 'follow',
      body: new File([inputEl.value], "{filename}")
    }})
    .then(response => {{
      if (response.redirected) {{
        window.location = response.url
      }}
    }})
    .catch(error => console.error('Error:', error));
  }}
   buttonEl.addEventListener('click', () => submit())
   inputEl.addEventListener('keydown', e => {{
    if (e.ctrlKey && e.key === "Enter") submit()
  }})
}})
""".format(req_path=req_path, filename=filename)
    )

    return HTMLDocument(
        body_els=(
            TextArea(text, rows=text.count('\n') + 1, style='width: 100%;',
                     id='textarea'),
            Button('submit', id='submit')
        ),
        head_els=(script,)
    )

###############################################################################
# Filesystem Directory Listing
###############################################################################

def _directory_listing_item(fs_path, href_prefix, filename):
    _fs_path = path.join(fs_path, filename)
    is_dir = path.isdir(_fs_path)
    href_suffix = '{}/'.format(filename) if is_dir else filename
    container = Div()
    # Add either a directory spacer or edit link.
    if is_dir:
        container.append_child(Span('----', style="margin-right: 1rem;"))
    else:
        container.append_child(Anchor(
            'edit',
            href=href_prefix + href_suffix + '?edit=1',
            style='text-decoration: none; margin-right: 1rem;'
        ))
    # Add the item link.
    container.append_child(Anchor(
        href_suffix,
        href=href_prefix + href_suffix,
        style='text-decoration: none; margin-right: 1rem;'
    ))
    return container

def FilesystemDirectoryListing(fs_path, req_path):
    """Return a directory listing HTML page for the specified req_path.
    """
    href_prefix = '/_fs{}/'.format(
        ('/' + req_path.rstrip('/')) if req_path else ''
    )
    return HTMLDocument(
        body_els=[_directory_listing_item(fs_path, href_prefix, filename)
                  for filename in os.listdir(fs_path)],
        head_els=[Style('body {font-family: monospace; font-size: 1rem;}')]
    )
