import re
import time
import datetime as datetime

class BusData:
  def __init__(self, number, destination, timeLiteral, operator):
    self.number = number
    self.destination = destination
    self.timeLiteral = timeLiteral
    self.operator = operator
    self.time = prepare_departure_time(timeLiteral)

def prepare_departure_time(timeLiteral):

  now = datetime.datetime.today()

  if isTimeFormat(timeLiteral):
    parsed = datetime.datetime.strptime(timeLiteral, '%H:%M').time()
    dueAt = datetime.datetime.combine(now.date(), parsed)
    if dueAt < now:
      dueAt += datetime.timedelta(days = 1)
    return dueAt
  else:
    if timeLiteral == 'Due':
      dueMinutes = 0
    else:
      match = re.search(r'-?\d+', timeLiteral)
      if match is None:
        # e.g. "Cancelled": no due time, sort after real departures
        return datetime.datetime.max
      dueMinutes = max(0, int(match.group()))

    dueAt = now + datetime.timedelta(minutes = dueMinutes)
    return dueAt

def isTimeFormat(input):
    try:
        time.strptime(input, '%H:%M')
        return True
    except ValueError:
        return False