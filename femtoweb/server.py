
import asyncio
import json
import re
from traceback import print_exc

from collections import namedtuple


###############################################################################
# Types
###############################################################################

Request = namedtuple('Request', (
    'reader',
    'writer',
    'method',
    'path',
    'query',
    'headers',
    'body',
))

DEFAULT_RESPONSE_HEADERS = {
    'content-type': 'text/html',
    'connection': 'close',
}

class Response():
    CORS_ENABLED = True

    def __init__(self, status_int=None, headers=None, body=None):
        if status_int is not None:
            self.status_int = status_int

        _headers = DEFAULT_RESPONSE_HEADERS.copy()

        if self.CORS_ENABLED:
            _headers['access-control-allow-origin'] = '*'

        if hasattr(self, 'headers'):
            _headers.update(self.headers)
        if headers is not None:
            _headers.update(headers)
        self.headers = _headers

        self.body = body


class _200(Response):
    status_int = 200


class _303(Response):
    status_int = 303

    def __init__(self, location):
        Response.__init__(self, headers={'location': location})


class ErrorResponse(Response):
    headers = {'content-type': 'text/plain'}
    def __init__(self, details=None):
        body = '{} {}'.format(self.status_int, self.body)
        if details is not None:
            body = '{} - {}'.format(body, details)

        Response.__init__(self, body=body)


class _400(ErrorResponse):
    status_int = 400
    body = 'Invalid Request'


class _404(ErrorResponse):
    status_int = 404
    body = 'Not Found'


class _405(ErrorResponse):
    status_int = 405
    body = 'Method Not Allowed'


class _500(ErrorResponse):
    status_int = 500
    body = 'Server Error'


class _503(ErrorResponse):
    status_int = 503
    body = 'Service Unavailable'


###############################################################################
# Constants
###############################################################################

DEBUG = False

HTTP_DELIM = b'\r\n'

# Content Types
APPLICATION_JAVASCRIPT = 'application/javascript'
APPLICATION_JSON = 'application/json'
APPLICATION_OCTET_STREAM = 'application/octet-stream'
APPLICATION_PYTHON = 'application/x-python'
APPLICATION_SCHEMA_JSON = 'application/schema+json'
IMAGE_GIF = 'image/gif'
IMAGE_JPEG = 'image/jpeg'
IMAGE_PNG = 'image/png'
TEXT_CSS = 'text/css'
TEXT_HTML = 'text/html'
TEXT_PLAIN = 'text/plain'
TEXT_EVENT_STREAM = 'text/event-stream'

FILE_LOWER_EXTENSION_CONTENT_TYPE_MAP = {
    'css': TEXT_CSS,
    'gif': IMAGE_GIF,
    'html': TEXT_HTML,
    'jpeg': IMAGE_JPEG,
    'jpg': IMAGE_JPEG,
    'js': APPLICATION_JAVASCRIPT,
    'json': APPLICATION_JSON,
    'png': IMAGE_PNG,
    'py': APPLICATION_PYTHON,
    'schema.json': APPLICATION_SCHEMA_JSON,
    'txt': TEXT_PLAIN,
}

MAX_FILE_EXTENSION_SEGMENTS = max(
    k.count('.') + 1 for k in FILE_LOWER_EXTENSION_CONTENT_TYPE_MAP
)

DELETE = 'DELETE'
GET = 'GET'
POST = 'POST'
PUT = 'PUT'

###############################################################################
# Exceptions
###############################################################################

class HTTPServerException(Exception): pass

class ShortRead(HTTPServerException): pass
class ZeroRead(HTTPServerException): pass
class CouldNotParse(HTTPServerException): pass

###############################################################################
# Query Parameter Parsers
###############################################################################

def parsing_error():
    raise CouldNotParse

def as_type(t):
    def f(x):
        # Prevent casting of None, which str() will happily do.
        if x is None and t is not None:
            parsing_error()
        try:
            return t(x)
        except (TypeError, ValueError):
            parsing_error()
    return f

def as_choice(*choices):
    return lambda x: x if x in choices else parsing_error()

def as_nonempty(parser):
    def f(x):
        x = parser(x)
        return x if len(x) > 0 else parsing_error()
    return f

def with_default_as(parser, default):
    def f(x):
        try:
            return parser(x)
        except CouldNotParse:
            return default
    return f

def maybe_as(parser):
    def f(x):
        try:
            return parser(x)
        except CouldNotParse:
            return x if x is None else parsing_error()
    return f

###############################################################################
# Utility Functions
###############################################################################

_decode = lambda b: b.decode('ISO-8859-1')

get_file_extension_content_type = \
    lambda ext: FILE_LOWER_EXTENSION_CONTENT_TYPE_MAP.get(ext.lower(), None)

def get_file_path_content_type(fs_path):
    # Attempt to greedily match (i.e. the extension with the most segments) the
    # filename extension to a content type.
    splits = fs_path.rsplit('.', MAX_FILE_EXTENSION_SEGMENTS)
    num_segs = len(splits) - 1
    while num_segs > 0:
        ext = '.'.join(splits[-num_segs:])
        content_type = get_file_extension_content_type(ext)
        if content_type is not None:
            return content_type
        num_segs -= 1
    # Filename didn't match any definde content type so return the default
    # 'application/octet-stream'.
    return APPLICATION_OCTET_STREAM

def parse_uri(uri):
    if '?' not in uri:
        return uri, {}
    # TODO - URL unencoding
    path, query_string = uri.split('?')
    query = {}
    for pair_str in query_string.split('&'):
        kv = pair_str.split('=')
        kv_len = len(kv)
        if kv_len == 2:
            k, v = kv
            query[k] = v
        elif kv_len == 1:
            query[kv[0]] = None
        else:
            if DEBUG:
                print('Unparsable query param: "{}"'.format(pair_str))
    return path, query

async def parse_request(reader, writer):
    # Get the first 1024 bytes
    data = await reader.read(1024)
    if not data:
        raise ZeroRead

    # Consume the request line
    request_line, data = data.split(HTTP_DELIM, 1)
    method, uri, protocol_version = _decode(request_line).split()
    path, query = parse_uri(uri)

    # Parse the headers.
    headers = {}
    start_idx = 0
    end_idx = None
    while True:
        # Find the next delimiter index
        delim_idx = data[start_idx:].find(HTTP_DELIM)
        if delim_idx == -1:
            # No delimiter was found which probably indicates that our initial
            # read was a short one, so, for now, raise an exception and we can
            # come back later and do more reading if necessary.
            raise ShortRead

        end_idx = start_idx + delim_idx

        if delim_idx == 0:
            # We've reached the double CRLF chars that signal the end od the
            # header, so return the headers map and the rest of data as the
            # request body.
            body = data[end_idx + 2:]
            break

        # Delimiter found so parse the header key/value pair, lowercasing the
        # header name for internal consistency.
        k, v = _decode(data[start_idx : start_idx + delim_idx]).split(':', 1)
        headers[k.strip().lower()] = v.strip()
        start_idx = end_idx + 2

    return Request(
        reader=reader,
        writer=writer,
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=body,
    )

def parse_query_params(request, parser_map):
    """Apply parsers to the request query params.
    """
    query = request.query
    ok_params = {}
    bad_params = {}
    for k, parser in parser_map.items():
        v = query.get(k)
        try:
            ok_params[k] = parser(v)
        except CouldNotParse:
            bad_params[k] = v
    return ok_params, bad_params

###############################################################################
# Connection Handling
###############################################################################

async def send(writer, response, close=True):
    """Write a response to writer stream.
    """
    if DEBUG:
        print('sending response: {}'.format(response))
    writer.write('HTTP/1.1 {} OK\n'.format(response.status_int).encode())
    for k, v in response.headers.items():
        writer.write('{}: {}\n'.format(k, v).encode())
    writer.write(b'\n')
    await writer.drain()

    if response.body is not None:
        if not hasattr(response.body, 'readinto'):
            # Assume that body is a string and send it.
            writer.write(response.body.encode())
            await writer.drain()
        else:
            # Assume that body is a file-type object and iterate over it
            # sending each chunk to avoid exhausting the available memory by
            # doing it all in one go.
            chunk_mv = memoryview(bytearray(1024))
            num_bytes = 0
            while True:
                num_bytes = response.body.readinto(chunk_mv)
                if num_bytes == 0 or num_bytes is None:
                    break
                writer.write(chunk_mv[:num_bytes])
                await writer.drain()
    # Maybe close the writer.
    if close:
        writer.close()
        await writer.wait_closed()

async def service_connection(reader, writer):
    """Handle a new server connection.
    """
    try:
        request = await parse_request(reader, writer)
        if DEBUG:
            print('request: {}'.format(request))
        await dispatch(request)
    except KeyboardInterrupt:
        writer.close()
        await writer.wait_closed()
        raise
    except Exception as e:
        print_exc()
        try:
            await send(writer, _500(str(e)))
        except Exception:
            print_exc()
        writer.close()
        await writer.wait_closed()

async def serve(host='0.0.0.0', port='8000', backlog=5, enable_cors=True):
    """Start the webserver.
    """
    Response.CORS_ENABLED = enable_cors
    return await asyncio.start_server(
        service_connection,
        host,
        port,
        backlog=backlog
    )

###############################################################################
# Routing
###############################################################################

# Define a module-level variable to store (<pathRegex>, <allowedMethods>,
# <query_param_parser_map>, <func>) tuples for functions decorated with @route.
_routes = []

def route(path_pattern, methods=('GET',), query_param_parser_map=None):
    """A decorator to register a function as the handler for requests to the
    specified path regex pattern and send any returned response.
    """
    def decorator(func):
        """Return a function that will accept a request argument, invoke the
        handler, and send any response.
        """
        # If no line start/end chars are present in the path pattern, add both,
        # i.e. "^<path_pattern>$".
        if not path_pattern.startswith('^') and not path_pattern.endswith('$'):
            path_regex = re.compile('^{}$'.format(path_pattern))
        else:
            path_regex = re.compile(path_pattern)

        async def wrapper(request, *args, **kwargs):
            """Invoke the request handler and send any response.
            """
            response = await func(request, *args, **kwargs)
            if response is not None:
                await send(request.writer, response)

        # Register this wrapper for the path.
        _routes.append((path_regex, methods, query_param_parser_map, wrapper))
        return wrapper

    return decorator

async def dispatch(request):
    """Attempt to find and invoke the handler for the specified request path
    and return a bool indicating whether a handler was found.
    """
    any_path_matches = False
    for regex, methods, query_param_parser_map, func in _routes:
        match = regex.match(request.path)
        any_path_matches |= match is not None
        if match and request.method in methods:
            if query_param_parser_map is None:
                await func(request)
                return
            ok_params, bad_params = parse_query_params(
                request,
                query_param_parser_map
            )
            if not bad_params:
                await func(request, **ok_params)
            else:
                await send(
                    request.writer,
                    _400('invalid params: {}'.format(bad_params))
                )
            return

    if any_path_matches:
        # Send a Method-Not-Allowed response if any path matched.
        await send(request.writer, _405())
    else:
        # Otherwise, send a Not-Found respose.
        await send(request.writer, _404())

###############################################################################
# Request Handler Decorators
###############################################################################

def event_source(func):
    """A request handler wrapper to initialize an event source connection and pass
    a sender function to the handler.
    """
    async def wrapper(request, *args, **kwargs):
        # Send the event source response headers and keep the connection
        # open.
        res = Response(200, headers={
            'cache-control': 'no-cache',
            'content-type': TEXT_EVENT_STREAM
        })
        await send(request.writer, res, close=False)
        # Define a sender function that encodes and writes the data to the
        # event stream.
        writer = request.writer
        async def sender(data):
            writer.write(
                f'data: {json.dumps(data)}\n\n'.encode('utf-8')
            )
            await writer.drain()
        return await func(request, sender, *args, **kwargs)
    return wrapper

def json_request(func):
    """A request handler decorator that attempts to parse a JSON-encoded
    request body and pass it as an argument to the handler.
    """
    async def wrapper(request, *args, **kwargs):
        if request.headers.get('content-type') != APPLICATION_JSON:
            return _400('Expected Content-Type: {}'.format(APPLICATION_JSON))
        try:
            data = json.loads(request.body)
        except Exception:
            return _400('Could not parse request body as JSON')
        return await func(request, data, *args, **kwargs)
    return wrapper

def json_response(func):
    """A request handler decorator that JSON-encodes the Response body and sets
    the Content-Type to "application/json".
    """
    async def wrapper(*args, **kwargs):
        response = await func(*args, **kwargs)
        response.body = json.dumps(response.body)
        response.headers['content-type'] = 'application/json'
        return response
    return wrapper

###############################################################################
# CLI
###############################################################################

# Run the server if executed as a script.
if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(serve())
    event_loop.run_forever()