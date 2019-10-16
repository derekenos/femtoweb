# femtoweb

femtoweb is a minimal, low-quality Python HTTP server and web application framework that exists primarily to support the [iome](https://github.com/derekenos/iome) project.

## Branches and their compatibility

| branch | pairs well with |
| --- | --- | 
| [master](https://github.com/derekenos/femtoweb/tree/master) | Python 3.4 |
| [micropython](https://github.com/derekenos/femtoweb/tree/micropython) | Micropython 1.11 |


## Run the Server

If you're like me, you love to use Docker for basically everything even though it can be pretty terrible:

```
git clone git@github.com:derekenos/femtoweb
cd femtoweb
docker run -it -v `pwd`:/femtoweb -p 8000:80 python:3.4 python /femtoweb/serve.py
```

Here's what those `docker` args mean:

- `run` - run a command in a new container
- `-it` - use interactive mode and allocate a terminal
- ``-v `pwd`:/femtoweb`` - mount the current directory inside the container as `/femtoweb`
- `-p 8000:80` - expose the container port 80 as local port 8000
- `python:3.4` - use the default Python v3.4 image
- `python /femtoweb/serve.py` -  command to execute inside the container to start the server

If all goes well, when you point a web browser at `localhost:8000` you'll see the text:
```
404 Not Found
```
Looks good to me :thumbsup:

You're seeing this because, by default, the root path (i.e. `/`) is not routed to anything. If you go over to `localhost:8000/_fs` you'll hit the [`filesystem` endpoint defined in `default_http_endpoints`](https://github.com/derekenos/femtoweb/blob/master/default_http_endpoints.py#L128) that allows you to navigate the local filesystem.

To demonstrate adding a handler for the root path, add the following [here in `serve.py`](https://github.com/derekenos/femtoweb/blob/master/serve.py#L3), and CTRL-C / re-execute that `docker` command:

```
from server import route, _200, GET

@route('/', methods=(GET,))
def home(request):
    return _200(body="Hello from femtoweb!")
```

Now when you surf over to `http://localhost:8000/` you should see:

```
Hello from femtoweb!
```

