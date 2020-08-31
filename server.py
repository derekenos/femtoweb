
import binascii
import hashlib
import json
import re
import socket
import sys
from collections import namedtuple

from uwebsocket import websocket


###############################################################################
# Types
###############################################################################

Request = namedtuple('Request', (
    'connection',
    'method',
    'path',
    'query',
    'headers',
    'body',
))

DEFAULT_RESPONSE_HEADERS = {
    'Content-Type': 'text/html',
    'Connection': 'close',
}

class Response():
    def __init__(self, status_int=None, headers=None, body=None):
        if status_int is not None:
            self.status_int = status_int

        _headers = DEFAULT_RESPONSE_HEADERS.copy()
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
        Response.__init__(self, headers={'Location': location})


class ErrorResponse(Response):
    headers = {'Content-Type': 'text/plain'}
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

APPLICATION_JAVASCRIPT = 'application/javascript'
APPLICATION_JSON = 'application/json'
APPLICATION_PYTHON = 'application/x-python'
IMAGE_GIF = 'image/gif'
IMAGE_JPEG = 'image/jpeg'
IMAGE_PNG = 'image/png'
TEXT_HTML = 'text/html'
TEXT_PLAIN = 'text/plain'

FILE_LOWER_EXTENSION_CONTENT_TYPE_MAP = {
    'js': APPLICATION_JAVASCRIPT,
    'json': APPLICATION_JSON,
    'gif': IMAGE_GIF,
    'jpeg': IMAGE_JPEG,
    'jpg': IMAGE_JPEG,
    'png': IMAGE_PNG,
    'html': TEXT_HTML,
    'py': APPLICATION_PYTHON,
    'txt': TEXT_PLAIN,
}

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

HTTP_DELIM = b'\r\n'


_decode = lambda b: b.decode('ISO-8859-1')


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


def parse_request(connection):
    # Get the first 1024 bytes
    data = connection.recv(1024)
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

        # Delimiter found so parse the header key/value pair.
        k, v = _decode(data[start_idx : start_idx + delim_idx]).split(':', 1)
        headers[k.strip()] = v.strip()
        start_idx = end_idx + 2

    return Request(
        connection=connection,
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=body,
    )

get_file_extension_content_type = \
    lambda ext: FILE_LOWER_EXTENSION_CONTENT_TYPE_MAP.get(ext.lower(), None)

get_file_path_content_type = \
    lambda fs_path: get_file_extension_content_type(fs_path.rsplit('.', 1)[1])


###############################################################################
# Connection Handling
###############################################################################

def service_connection(s, conn, addr):
    # Is the socket accessible via the connection object?
    if DEBUG:
        print('Got a connection from: {}'.format(str(addr)))

    try:
        request = parse_request(conn)
        if DEBUG:
            print('request: {}'.format(request))
        dispatch(request)
    except KeyboardInterrupt:
        s.close()
        raise
    except Exception as e:
        sys.print_exception(e)
        try:
            send(conn, _500(str(e)))
        except Exception as e:
            sys.print_exception(e)
        conn.close()


def serve():
    # Create a socket.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind it to port 80.
    s.bind(('', 80))
    # Start listening for connections with a max buffer of 5 pending.
    s.listen(5)
    # Blocking mode was causing input timer period to be a constant 100mS?
    s.setblocking(True)

    while True:
        try:
            conn, addr = s.accept()
            service_connection(s, conn, addr)
        except OSError:
            pass


def send(connection, response):
    connection.send('HTTP/1.1 {} OK\n'.format(response.status_int).encode())
    for k, v in response.headers.items():
        connection.send('{}: {}\n'.format(k, v).encode())
    connection.send(b'\n')

    if response.body is not None:
        if not hasattr(response.body, 'read'):
            # Assume that body is a string and send it.
            connection.sendall(response.body.encode())
        else:
            # Assume that body is a file-type object and iterate over it
            # sending each chunk to avoid exhausting the available memory by
            # doing it all in one go.
            chunk = None
            while True:
                chunk = response.body.read(2048)
                if not chunk:
                    break
                connection.send(chunk)

    connection.close()


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

        def wrapper(request, *args, **kwargs):
            """Invoke the request handler and send any response.
            """
            response = func(request, *args, **kwargs)
            if response is not None:
                send(request.connection, response)

        # Register this wrapper for the path.
        _routes.append((path_regex, methods, query_param_parser_map, wrapper))
        return wrapper

    return decorator


def as_json(func):
    """A request handler decorator that JSON-encodes the Response body and sets
    the Content-Type to "application/json".
    """
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        response.body = json.dumps(response.body)
        response.headers['Content-Type'] = 'application/json'
        return response
    return wrapper


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


def dispatch(request):
    """Attempt to find and invoke the handler for the specified request path
    and return a bool indicating whether a handler was found.
    """
    any_path_matches = False
    for regex, methods, query_param_parser_map, func in _routes:
        match = regex.match(request.path)
        any_path_matches |= match is not None
        if match and request.method in methods:
            if query_param_parser_map is None:
                func(request)
                return
            ok_params, bad_params = parse_query_params(
                request,
                query_param_parser_map
            )
            if not bad_params:
                func(request, **ok_params)
            else:
                send(
                    request.connection,
                    _400('invalid params: {}'.format(bad_params))
                )
            return

    if any_path_matches:
        # Send a Method-Not-Allowed response if any path matched.
        send(request.connection, _405())
    else:
        # Otherwise, send a Not-Found respose.
        send(request.connection, _404())


###############################################################################
# Websockets
###############################################################################

def do_websocket_server_handshake(request):
    """ Adapated from the websocket_helper.py:
    https://github.com/micropython/webrepl/blob/master/websocket_helper.py
    """
    webkey = request.headers.get('Sec-WebSocket-Key')
    if not webkey:
        raise OSError("Not a websocket request")
    respkey = bytes(webkey, 'ascii') + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    respkey = hashlib.sha1(respkey).digest()
    respkey = binascii.b2a_base64(respkey)[:-1]
    resp = b"""\
HTTP/1.1 101 Switching Protocols\r
Upgrade: websocket\r
Connection: Upgrade\r
Sec-WebSocket-Accept: %s\r
\r
""" % respkey
    request.connection.send(resp)


def as_websocket(func):
    """An endpoint function decorator that performs a websocket handshake and
    passes the websocket object as the second argument to the function.
    """
    def f(request, *args, **kwargs):
        # Set the socket to non-blocking.
        request.connection.setblocking(False)
        do_websocket_server_handshake(request)
        ws = websocket(request.connection, True)
        return func(request, ws, *args, **kwargs)
    return f


# Run the server if executed as a script.
if __name__ == '__main__':
    serve()
