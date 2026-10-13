import os

import requests
import zeep.exceptions
from zeep import Client
from zeep import xsd


from . import commons


HEADER = xsd.Element(
    "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}AccessToken",
    xsd.ComplexType(
        [
            xsd.Element(
                "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}" "TokenValue",
                xsd.String(),
            ),
        ]
    ),
)

WSDL = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2017-10-01"


def soap_client():
    commons.check_env_vars()

    return {
        "headers": [HEADER(TokenValue=os.environ["LDB_TOKEN"])],
        "client": Client(wsdl=WSDL),
    }


def get_departure_board_with_details(station_id: str, num_rows: int = 10):
    try:
        # the WSDL is downloaded when the client is created, so it can fail too
        soap_client_dict = soap_client()

        return soap_client_dict["client"].service.GetDepBoardWithDetails(
            crs=station_id, numRows=num_rows, _soapheaders=soap_client_dict["headers"]
        )
    except (requests.exceptions.RequestException, zeep.exceptions.Error) as e:
        raise commons.NationalRailException(
            f"National Rail API request error: {e}"
        ) from e
