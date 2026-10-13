import logging

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request

from . import kent, commons, view_model, data_updater

logger = logging.getLogger(__name__)

router = APIRouter()


class Stop(BaseModel):
    code: str


@router.get("/search/{search_string}")
async def search(search_string):
    return kent.stations_by_string(search_string)


# debugging only
@router.get("/next/{stop_code}")
def next_departures(stop_code):
    try:
        response = kent.next_services(stop_code)
    except commons.KentBusException as e:
        logger.warning(str(e))
        return {"status": "error", "message": str(e)}

    return {"status": "OK", "response": response}


# curl -X POST http://localhost:8000/kent/start-client -d {\"code\":\"2400A045760A\"}
@router.post("/start-client")
def start_client(stop: Stop, request: Request):
    try:
        kent.check_params(stop.code)
    except commons.KentBusException as e:
        logger.warning(str(e))
        return {"status": "error", "message": str(e)}

    # start board, replacing any client already running
    request.app.board_client.start(
        view_model.ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers,
        data_updater.DataUpdaterKentBus,
        {"stop_code": stop.code},
    )

    return {"status": "OK"}
