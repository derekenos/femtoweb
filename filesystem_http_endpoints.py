"""HTTP endpoints definitions for filesystem operations.
"""
from os import path
import os

from default_html_renderers import (
    HTMLDocument,
    HTMLAnchorElement,
    HTMLSpanElement,
    TextFileEditor,
)

from server import (
    APPLICATION_JSON,
    APPLICATION_PYTHON,
    DELETE,
    GET,
    POST,
    PUT,
    TEXT_HTML,
    TEXT_PLAIN,
    _200,
    _303,
    _404,
    _503,
    as_json,
    get_file_path_content_type,
    route,
    send,
)

###############################################################################
# Filesystem
###############################################################################

EDITABLE_CONTENT_TYPES = (
    APPLICATION_JSON,
    APPLICATION_PYTHON,
    TEXT_HTML,
    TEXT_PLAIN,
)

DEFAULT_PUBLIC_ROOT = path.join(path.dirname(__file__), 'public')

###############################################################################
# Endpoint helpers
###############################################################################

def _fs_GET(public_root, req_path):
    """Handle a filesystem GET request.
    """
    fs_path = path.join(public_root, req_path)
    if not path.exists(fs_path):
        return _404()

    if not path.isdir(fs_path):
        # The requested path is not a directory. Attempt to return the file.
        content_type = get_file_path_content_type(fs_path)
        return _200(
            headers={'content-type': content_type},
            body=open(fs_path, 'rb')
        )

    # The request path is a directory, return an HTML directory listing.
    # Return the directory listing
    filenames = os.listdir(fs_path)

    # Define some styles.
    head = """
    <style>
      body {
        font-family: monospace;
        font-size: 1rem;
      }
    </style>
    """

    # Generate the HTML body.
    body = ''
    href_prefix = '/_fs{}/'.format(
        ('/' + req_path.rstrip('/')) if req_path else ''
    )
    for filename in filenames:
        _fs_path = path.join(fs_path, filename)
        is_dir = path.isdir(_fs_path)

        href_suffix = '{}/'.format(filename) if is_dir else filename

        body += '<div>'
        # Add either a directory spacer or edit link.
        if is_dir:
            body += HTMLSpanElement('----', style="margin-right: 1rem;")
        else:
            body += HTMLAnchorElement(
                'edit',
                href=href_prefix + href_suffix + '?edit=1',
                style='text-decoration: none; margin-right: 1rem;'
            )
        # Add the item link.
        body += HTMLAnchorElement(
            href_suffix,
            href=href_prefix + href_suffix,
            style='text-decoration: none; margin-right: 1rem;'
        )
        body += '</div>'

    return _200(body=HTMLDocument(body, head))

def _fs_GET_edit(public_root, req_path, create):
    fs_path = path.join(public_root, req_path)
    if path.exists(fs_path):
        text = open(fs_path, 'rb').read().decode('utf-8')
    elif not create:
        return _404()
    else:
        text = ''
    body = TextFileEditor(req_path, text)
    return _200(body=body)


async def _fs_PUT(public_root, req_path, request):
    """Handle a filesystem PUT request.
    """
    # TODO - validate the request (e.g. check for avail drive space, whether
    # directory already exists with same name, etc.))
    if request.headers.get('expect') == '100-continue':
        request.writer.write('HTTP/1.1 100 Continue\r\n')
        request.writer.write('\r\n')
        await request.writer.drain()

    # TODO - write to a temporary file and rename to target on success.
    MAX_CHUNK_BYTES = 1024
    with open(path.join(public_root, req_path), 'wb') as fh:
        bytes_remaining = int(request.headers['content-length'])

        # First yield from the body if non-empty.
        body = request.body
        while body:
            chunk = body[:MAX_CHUNK_BYTES]
            body = body[MAX_CHUNK_BYTES:]
            fh.write(chunk)
            bytes_remaining -= len(chunk)

        # If we need more bytes, receive them from the socket.
        while bytes_remaining:
            chunk = await request.reader.read(
                min(bytes_remaining, MAX_CHUNK_BYTES)
            )
            fh.write(chunk)
            bytes_remaining -= len(chunk)

    return _303(location='/_fs/{}'.format(req_path))

def _fs_DELETE(public_root, req_path):
    """Handle a filesystem DELETE request.
    """
    fs_path = path.join(public_root, req_path)
    if not path.exists(fs_path):
        return _404()
    os.remove(fs_path)
    return _200()

###############################################################################
# Filesystem operation dispatcher
###############################################################################

async def filesystem(request, public_root):
    """Handle filesystem operations.
    """
    # Strip any leading slash to prevent path.join() from resolving relative to
    # the filesystem root.
    req_path = request.path[4:].lstrip('/')

    if request.method == 'GET':
        if (request.query.get('edit') == '1' and
            get_file_path_content_type(req_path) in EDITABLE_CONTENT_TYPES):
            create = request.query.get('create') == '1'
            return _fs_GET_edit(public_root, req_path, create)
        else:
            return _fs_GET(public_root, req_path)

    elif request.method == 'PUT':
        return await _fs_PUT(public_root, req_path, request)

    elif request.method == 'DELETE':
        return _fs_DELETE(public_root, req_path)

###############################################################################
# Route attacher
###############################################################################

def attach(public_root=DEFAULT_PUBLIC_ROOT):
    """Add a route for the filesystem operation endpoints.
    """
    @route('^((/_fs/?)|(/_fs/.+))$', methods=(GET, PUT, DELETE))
    async def _filesystem(request):
        return await filesystem(request, public_root)
