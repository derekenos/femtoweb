
import machine

from femtoweb.server import (
    _200,
    GET,
    POST,
    route,
    send,
)

def attach():
    @route('/_reset', methods=(GET, POST))
    async def reset(request):
        """Reset the device.
        """
        # Manually send the response prior to calling machine.reset
        await send(request.writer, _200())
        machine.reset()
