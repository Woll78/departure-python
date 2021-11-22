import threading
import time
import logging

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request

from . import nexus, commons, view_model, data_updater

logger = logging.getLogger(__name__)

router = APIRouter()


class Stop(BaseModel):
    code: str


@router.get("/search/{search_string}")
async def search(search_string):
    return nexus.stations_by_string(search_string)


# debugging only
@router.get("/next/{stop_code}")
async def next_departures(stop_code):
    # request next services

    try:
        response = nexus.next_services(stop_code)
    except commons.NexusBusException as e:
        logger.warning(str(e))
        return {"status": "error", "message": str(e)}

    # return next services
    return {
        "status": "OK",
        "response": response,
    }


# curl -X POST http://localhost:8000/nexus/start-client -d {\"code\":\"vic\"}
@router.post("/start-client")
async def start_client(stop: Stop, request: Request):
    # check parameters
    stop_code = stop.code
    #try:
    #    nexus.check_params(stop_code)
    #except commons.NexusBusException as e:
    #    logger.warning(str(e))
    #    return {"status": "error", "message": str(e)}

    # stop board client if already running
    if request.app.board_client.running:
        request.app.board_client.running = False
        time.sleep(1)

    # start board
    threading.Thread(
        target=request.app.board_client.run,
        args=[
            view_model.ViewModelNexusBus_192_32_3_Rows_To_ProtocolBuffers,
            data_updater.DataUpdaterNexusBus,
            {"stop_code": stop_code},
        ],
    ).start()

    return {"status": "OK"}
