
import os
from os import path

from .htmlephant import (
    Anchor,
    Button,
    Div,
    DocumentStream,
    Script,
    Span,
    Style,
    Textarea,
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

    return DocumentStream(
        body_els=(
            Textarea(text, rows=text.count('\n') + 1, style='width: 100%;',
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
        container.children.append(Span('----', style="margin-right: 1rem;"))
    else:
        container.children.append(Anchor(
            'edit',
            href=href_prefix + href_suffix + '?edit=1',
            style='text-decoration: none; margin-right: 1rem;'
        ))
    # Add the item link.
    container.children.append(Anchor(
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
    return DocumentStream(
        body_els=[_directory_listing_item(fs_path, href_prefix, filename)
                  for filename in os.listdir(fs_path)],
        head_els=[Style('body {font-family: monospace; font-size: 1rem;}')]
    )
