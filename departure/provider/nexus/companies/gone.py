import requests

from departure.provider.nexus.bus_data_model import BusData
from bs4 import BeautifulSoup

class GONE:

    def fetch(self, stopId):

        list1 = []
        # Caledonian Street
            #410000010502")
        # Post Office
            #41000010JARA
        page = requests.get('https://www.gonortheast.co.uk/stops/' + stopId)

        soup = BeautifulSoup(page.content, 'html.parser')
        board_markup = soup.find('div', class_='departure-board')
        if board_markup is None:
            return

        journey_elements = board_markup.findAll('a', class_='single-visit')

        for visit_element in journey_elements:

            bus_content = visit_element.find('div',
                class_='single-visit__content')
            time_content = visit_element.find('div',
                class_='single-visit__time')

            number = bus_content.find('p', class_='single-visit__name'
                                  ).getText().strip()
            destination = bus_content.find('p',
                class_='single-visit__description').getText().strip()
            time = time_content.find('div', class_='single-visit__time'
                                 ).getText().strip()

            journey = BusData(number, destination, time, "Go North East")

            yield journey