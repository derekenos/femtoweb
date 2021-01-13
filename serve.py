
import asyncio

from femtoweb import filesystem_endpoints
from femtoweb.server import serve

###############################################################################
# event_source decorator example
###############################################################################

import asyncio

from femtoweb.server import (
    GET,
    event_source,
    route,
)

@route('/events', methods=(GET,))
@event_source
async def events(request, emitter):
    n = 0
    while True:
        await emitter(n)
        n += 1
        await asyncio.sleep(1)

###############################################################################
# json_response decorator example
###############################################################################

from datetime import datetime

from femtoweb.server import (
    _200,
    GET,
    json_response,
    route,
)

@route('/time', methods=(GET,))
@json_response
async def get_time(request):
   return _200(body={'currentTime': datetime.now().isoformat()})

###############################################################################
# CLI
###############################################################################

if __name__ == '__main__':
    filesystem_endpoints.attach()
    event_loop = asyncio.get_event_loop()
    event_loop.create_task(serve())
    event_loop.run_forever()
