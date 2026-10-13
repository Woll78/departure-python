import re
import time
import datetime as datetime

# a bus running at least this many minutes behind its timetable is shown as delayed
DELAYED_AFTER_MINUTES = 1

class BusData:
  def __init__(self, number, destination, timeLiteral, operator, delay_minutes=0):
    self.number = number
    self.destination = destination
    self.timeLiteral = timeLiteral
    self.operator = operator
    self.delay_minutes = delay_minutes
    self.time = prepare_departure_time(timeLiteral)

  @property
  def is_delayed(self):
    return self.delay_minutes >= DELAYED_AFTER_MINUTES

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