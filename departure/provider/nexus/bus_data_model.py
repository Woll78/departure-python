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
    dueAt = now.date() + time.strptime(timeLiteral, '%H:%M')
    return dueAt
  else:
    if timeLiteral == 'Due':
      dueMinutes = 0
    else: 
      dueMinutes = [int(word) for word in timeLiteral.split() if word.isdigit()][0]

    dueAt = now + datetime.timedelta(minutes = dueMinutes)
    return dueAt

def isTimeFormat(input):
    try:
        time.strptime(input, '%H:%M')
        return True
    except ValueError:
        return False