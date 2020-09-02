import os
import gc
from binascii import hexlify

from ._os import path

from . import default_html_renderers as renderers
from .server import (
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
    route,
    get_file_path_content_type,
)


EDITABLE_CONTENT_TYPES = (
    APPLICATION_JSON,
    APPLICATION_PYTHON,
    TEXT_HTML,
    TEXT_PLAIN,
)


###############################################################################
# Filesystem
###############################################################################

def _fs_GET(fs_path):
    """Handle a filesystem GET request.
    """
    if not path.exists(fs_path):
        return _404()

    if path.isdir(fs_path):
        # Return the directory listing
        filenames = os.listdir(fs_path)
        body = ''
        for filename in filenames:
            _fs_path = path.join(fs_path, filename)
            is_dir = path.isdir(_fs_path)
            body += (
                '<div>'
                '  <a href="/_fs{}" '
                '     style="text-decoration: none;">'
                '    {}'
                '  </a>'
                '</div>'
            ).format(
                _fs_path,
                '{}/'.format(filename) if is_dir else filename
            )

        return _200(body=body)

    # Return what we assume to be a file
    content_type = get_file_path_content_type(fs_path)
    return _200(
        headers={'Content-Type': content_type},
        body=open(fs_path, 'rb')
    )


def _fs_GET_edit(fs_path, create):
    if path.exists(fs_path):
        text = open(fs_path, 'rb').read().decode('utf-8')
    elif not create:
        return _404()
    else:
        text = ''
    body = renderers.TextFileEditor(fs_path, text)
    return _200(body=body)


async def _fs_PUT(fs_path, request):
    """Handle a filesystem PUT request.
    """
    # TODO - validate the request (e.g. check for avail drive space, whether
    # directory already exists with same name, etc.))
    if request.headers.get('Expect') == '100-continue':
        request.writer.write('HTTP/1.1 100 Continue\r\n')
        request.writer.write('\r\n')
        await request.writer.drain()

    async def chunker(max_size):
        bytes_remaining = int(request.headers['Content-Length'])

        # First yield from the body if non-empty.
        body = request.body
        while body:
            chunk = body[:max_size]
            body = body[max_size:]
            yield chunk
            bytes_remaining -= len(chunk)

        # If we need more bytes, receive them from the socket.
        while bytes_remaining:
            chunk = await request.reader.read(min(bytes_remaining, max_size))
            yield chunk
            bytes_remaining -= len(chunk)

    # TODO - write to a temporary file and rename to target on success.
    with open(fs_path, 'wb') as fh:
        for chunk in chunker(1024):
            fh.write(chunk)

    return _303(location='/_fs{}'.format(fs_path))


def _fs_DELETE(fs_path):
    """Handle a filesystem DELETE request.
    """
    if not path.exists(fs_path):
        return _404()
    os.remove(fs_path)
    return _200()


@route('^((/_fs/?)|(/_fs/.+))$', methods=(GET, PUT, DELETE))
async def filesystem(request):
    """Handle filesystem operations.
    """
    fs_path = request.path[4:] or '/'

    if request.method == 'GET':
        if (request.query.get('edit') == '1' and
            get_file_path_content_type(fs_path) in EDITABLE_CONTENT_TYPES):
            create = request.query.get('create') == '1'
            return _fs_GET_edit(fs_path, create)
        else:
            return _fs_GET(fs_path)

    elif request.method == 'PUT':
        return await _fs_PUT(fs_path, request)

    elif request.method == 'DELETE':
        return _fs_DELETE(fs_path)
