import time
import datetime

def str_to_date(string):
  if len(string):
    year,month,day = map(int,string.split('-'))
    return datetime.date(year,month,day)
  
def date_to_str_tuple(date):
  year,month,day = str(date).split('-')
  return year,month,day

def gmt_today():
    gmt  = time.gmtime()
    return datetime.date(gmt[0],gmt[1],gmt[2])
  
def gmt_yesterday():
    timedelta = datetime.timedelta(days = 1)
    return gmt_today()-timedelta

def gmt_now():
    gmt  = time.gmtime()
    return datetime.datetime(gmt[0],gmt[1],gmt[2],gmt[3],gmt[4],gmt[5])

def midnight_flag():
    now = gmt_now() 
    if now.hour == 0 and now.minute < 10:
            return True
    else:
            return False
        
def week_start_flag():
    today = gmt_today()
    if today.isoweekday() == 1:
        return True
    else:
        return False
    

def month_start_flag():
    today = gmt_today()
    if today.day == 1:
        return True
    else:
        return False

def minute_expiration():
    now = gmt_now()
    minute = now.minute
    second = now.second
    elapsed = (minute % 10)*60+second
    #Countdown till the next 10 minute mark
    return 600-elapsed

def day_expiration():
    now = gmt_now()
    hour = now.hour
    minute = now.minute
    second = now.second
    elapsed = hour * 3600 + minute * 60 + second
    #Countdown till midnight
    return 86400 - elapsed
    