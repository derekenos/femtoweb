
import asyncio

import filesystem_http_endpoints
from server import serve

if __name__ == '__main__':
    filesystem_http_endpoints.attach()
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(serve())
    event_loop.run_forever()
