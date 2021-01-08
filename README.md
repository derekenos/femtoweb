# femtoweb

femtoweb is an asynchronous Python HTTP server and web application framework that exists primarily for use with Micropython in support of my various IOT projects (e.g. [iome](https://github.com/derekenos/iome)).

## Branches and their compatibility

| branch | pairs well with |
| --- | --- | 
| [master](https://github.com/derekenos/femtoweb/tree/master) | Python 3.7 |
| [micropython](https://github.com/derekenos/femtoweb/tree/micropython) | Micropython 1.13 |


## Run the Server

Executing `serve.py` is just like executing `server.py` but with filesystem endpoints attached.
```
python3.7 serve.py
```

If all goes well, when you point a web browser at `localhost:8000` you'll see the text:
```
404 Not Found
```
Looks good to me :thumbsup:

You're seeing this because, by default, the root path (i.e. `/`) is not routed to anything. If you go over to `localhost:8000/_fs` you'll hit the [`filesystem` endpoint defined in `filesystem_http_endpoints`](https://github.com/derekenos/femtoweb/blob/master/filesystem_http_endpoints.py) that allows you to navigate the local filesystem.

To demonstrate adding a handler for the root path, add the following [here in `serve.py`](https://github.com/derekenos/femtoweb/blob/master/serve.py#L6), and restart the server.

```
from server import route, _200, GET

@route('/', methods=(GET,))
async def home(request):
    return _200(body="Hello from femtoweb!")
```

Now when you surf over to `http://localhost:8000/` you should see:

```
Hello from femtoweb!
```

## The Features

### routing

Registering a function as the handler for requests to a certain URL path is accomplished using the [route](https://github.com/derekenos/femtoweb/blob/master/server.py#L366) decorator.

#### Usage

```
@route(path_pattern, methods=('GET',), query_param_parser_map=None)
async def handler(request):
   ... fun stuff ...
   return Response()
```

Where:

- `path_pattern` is a regular expression string that will be used to match against the request path. Note that if you do not specifying a leading `^` or trailing `$`, [both will be automatically added for you](https://github.com/derekenos/femtoweb/blob/master/server.py#L377).
- `methods` is an iterable of one or more of [DELETE, GET, POST, PUT](https://github.com/derekenos/femtoweb/blob/master/server.py#L130-L133)
- `query_param_parser_map` is an optional `<param-name>` -> `<parser-func>` map that will be used to parse request params. Any missing required or invalid params will result in a `400 - Bad Request` response.
- `Response` is a [Response](https://github.com/derekenos/femtoweb/blob/master/server.py#L29) object

#### Example

This route simply returns the value of the `text` request query parameter.
```
@route('/echo', methods=(GET,), query_param_parser_map={
    'text': as_type(str)
})
async def echo(request, text):
    return _200(body=text)
```

#### Available Query Param Parser Functions
- [as_type(t)](https://github.com/derekenos/femtoweb/blob/5a0b8c960d88bda274c705832a10686f93ec5d71/server.py#L155) - must be of type `t`
- [as_choice(\*choices)](https://github.com/derekenos/femtoweb/blob/5a0b8c960d88bda274c705832a10686f93ec5d71/server.py#L167) - must be one of `*choices`
- [as_nonempty(parser)](https://github.com/derekenos/femtoweb/blob/5a0b8c960d88bda274c705832a10686f93ec5d71/server.py#L171) - must be non-empty
- [with_default_as(parser, default)](https://github.com/derekenos/femtoweb/blob/5a0b8c960d88bda274c705832a10686f93ec5d71/server.py#L178) - return `default` if parser fails
- [maybe_as(parser)](https://github.com/derekenos/femtoweb/blob/5a0b8c960d88bda274c705832a10686f93ec5d71/server.py#L187): return `None` if parser fails

#### Order and Methods

The order in which you define routes matters.

For example, if you define:
```
@route('.*', methods=(GET,))
async def catchall(request):
    ...
    
@route('/', methods=(GET, POST))
async def home(request):
    ...
```
A `GET` to `/` can not reach the `home` handler because the `catchall` handler was defined first and its path regex will match everything. A `POST` to `/`, however, will reach `home` because `catchall` only supports `GET`.

You can also route the same pattern multple times but for different methods.
For example, `home` could be split into two functions, one for `GET` and one for `POST`:

```
@route('/', methods=(GET,))
async def home_GET(request):
    ...

@route('/', methods=(POST,))
async def home_POST(request):
    ...
```

### as_json

You can use the [`as_json` decorator](https://github.com/derekenos/femtoweb/blob/master/server.py#L395) in conjunction with `route` to automatically encode the `Response.body` as JSON, e.g.:

```
@route('/time', methods=(GET,))
@as_json
async def get_time(request):
   return _200(body={'currentTime': datetime.now().isoformat()})
```

This will make the `/time` endpoint respond with the body `{"currentTime": "2019-10-16T20:49:22.543090"}` and `Content-Type: application/json`.


### File Operations

[filesystem_endpoints.py](https://github.com/derekenos/femtoweb/blob/7df10a30115f08736a6055e44e3fd924d4ee3601/filesystem_endpoints.py) implements a [/\_fs](https://github.com/derekenos/femtoweb/blob/7df10a30115f08736a6055e44e3fd924d4ee3601/filesystem_endpoints.py#L152) endpoint that supports file operations.

#### GET Operations

Currently, a `GET` to:

- a directory-type object path will respond with an HTML page comprising a list of links
- a file-type object path will respond with the file itself, setting the response `Content-Type` as appropriate

##### In-browser File Editor

[filesystem_views.py](https://github.com/derekenos/femtoweb/blob/7df10a30115f08736a6055e44e3fd924d4ee3601/filesystem_views.py) defines a super-simple [TextFileEditor](https://github.com/derekenos/femtoweb/blob/7df10a30115f08736a6055e44e3fd924d4ee3601/filesystem_views.py#L20) in-browser editor for plain text files that you can access by specifying the `edit=1` URL arg, e.g.:
`http://localhost:8000/_fs/hello.txt?edit=1`

Once you're done editing, you can click the `Submit` button or press `CTRL-Enter` to submit your changes, after which it will automatically redirect to the non-edit URL for the file.

Note that:

- You can create new files by also specifying `create=1`, e.g. ``http://localhost:8000/_fs/newfile.txt?edit=1&create=1`
- No validation is currently performed on the submitted data, so if youre editing a JSON file and you submit something that isn't valid JSON, you won't know until your application tries to read it, and probably crashes.


#### curl

You can use `curl` to manipulate the filesystem from the command line:

```
# Create or update a file
curl --upload-file file.txt `http://localhost:8000/_fs/file.txt

# Get a file
curl `http://localhost:8000/_fs/file.txt

# Delete a file
curl -X DELETE `http://localhost:8000/_fs/file.txt
```

