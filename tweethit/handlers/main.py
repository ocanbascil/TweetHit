import helipad
from google.appengine.api import taskqueue

from tweethit.utils.time_util import gmt_today,date_to_str_tuple
from tweethit.model import Store,DAILY,WEEKLY,MONTHLY
from tweethit.query import get_renderer_query_for_frequency

from config import DEBUG_MODE,TEMPLATE_PRODUCT_COUNT
import secret
import logging


import time
import datetime
from collections import defaultdict

helipad.root('tweethit').template_root('static/templates/')

root_url = 'http://localhost:8000'
#root_url = 'http://www.tweethit.com'

def create_day_href(locale,date,day_delta,root):
  date += datetime.timedelta(days = day_delta)
  year,month,day = date_to_str_tuple(date)
  return root+'/'+locale+'/day/'+year+'/'+month+'/'+day+'/'

def create_week_href(locale,date,week_delta,root):
  date += datetime.timedelta(weeks = week_delta)
  year,month,day = date_to_str_tuple(date)
  return root+'/'+locale+'/week/'+year+'/'+month+'/'+day+'/'

def create_month_href(locale,date,month_delta,root):
  date += datetime.timedelta(days = 30*month_delta)
  year,month,day = date_to_str_tuple(date)
  return root+'/'+locale+'/month/'+year+'/'+month+'/'
  
def create_template_data(locale,frequency,date,request,**kwargs):
    
  current_date = gmt_today()
  current_period_flag = False
  query_cache_expiration = 0
  store_key = Store.key_for_locale(locale)
  query = get_renderer_query_for_frequency(frequency,date,store_key)
  result_data = {}
  
  if len(request.query_string) > 0:
    result_data['query_string'] = '?'+request.query_string
    request_url  = request.url[:request.url.find('?')]
  else:
    result_data['query_string'] = ''
    request_url  = request.url
      
  #Debugger for turkey ban filter
  try:
      request.params['ban']
      root = 'http://tweethitapp.appspot.com'
  except KeyError:
      root = root_url
      
  if frequency == DAILY:  
    result_data['next_href'] = create_day_href(locale, date, 1,root)
    result_data['prev_href'] = create_day_href(locale, date, -1,root)
    if date == current_date:
      current_period_flag = True

  elif frequency == WEEKLY: 
    result_data['next_href'] = create_week_href(locale, date, 1,root)
    result_data['prev_href'] = create_week_href(locale, date, -1,root)
    if date.year == current_date.year and \
    date.isocalendar()[1] == current_date.isocalendar()[1]:
      current_period_flag = True

  elif frequency == MONTHLY:
    if date.year == current_date.year and \
    date.month == current_date.month:
      current_period_flag = True
    result_data['next_href'] = create_month_href(locale, date, 1,root)
    result_data['prev_href'] = create_month_href(locale, date, -1,root) 

  else:
      raise RendererException('Problem creating template data for \
      locale: %s, frequency: %s, kwargs: %s' %(locale,frequency,kwargs))
      
  groups = defaultdict(int)
  products = query.fetch(TEMPLATE_PRODUCT_COUNT)
  
  for item in products:
      groups[item.product_group] += 1
        
  result_data['date'] = date
  result_data['current_period_flag'] = current_period_flag
  result_data['products'] = products
  result_data['groups'] = groups
  result_data['assoc_id'] = secret.ASSOCIATE_DICT[locale]
  result_data['root_url'] = root
  result_data['daily_ranking_href'] = root+'/'+locale+'/day/'
  result_data['weekly_ranking_href'] = root+'/'+locale+'/week/'
  result_data['monthly_ranking_href'] = root+'/'+locale+'/month/'
  
  return result_data
      
class RendererException(Exception):
   
  def __init__(self, message):
    self.message = message
  def __str__(self):
    return repr(self.message) 
        
class MainHandler(helipad.Handler):
  def get(self):
    date = gmt_today()
    locale = 'us'
    template_dict = create_template_data(locale, DAILY, date,self.request)
    self.response.headers["Cache-Control"]="public; max-age=300;"
    return self.template('ranking_daily.html', template_dict)  
             
class LocaleHandler(helipad.Handler):
  def get(self,locale):
    date = gmt_today()
    self.response.headers["Cache-Control"]="public; max-age=300;"
    template_dict = create_template_data(locale, 'daily', date,self.request)
    return self.template('ranking_daily.html', template_dict)

        
class DayHandler(helipad.Handler):
  def get(self,locale,year,month,day):
    date = datetime.date(int(year),int(month),int(day))
    
    template_dict = create_template_data(locale, 'daily', date,self.request)
    self.response.headers["Cache-Control"]="public; max-age=300;"
    return self.template('ranking_daily.html', template_dict)  
        
class WeekHandler(helipad.Handler):
  def get(self,locale,year,month,day):

    date = datetime.date(int(year),int(month),int(day))
    template_dict = create_template_data(locale,'weekly', date,self.request)
    self.response.headers["Cache-Control"]="public; max-age=300;"
    return self.template('ranking_weekly.html', template_dict)  
        
class MonthHandler(helipad.Handler):
  def get(self,locale,year,month):
      
    date = datetime.date(int(year),int(month),15)
    template_dict = create_template_data(locale,'monthly', date,self.request)
    self.response.headers["Cache-Control"]="public; max-age=300;"
    return self.template('ranking_monthly.html', template_dict)
    
class CurrentDayHandler(helipad.Handler):
  def get(self,locale):
    date = gmt_today()
    template_dict = create_template_data(locale, 'daily', date,self.request)
    self.response.headers["Cache-Control"]="public; max-age=300;"
    return self.template('ranking_daily.html', template_dict)  
        
class CurrentWeekHandler(helipad.Handler):
  def get(self,locale):
    date = gmt_today()
    template_dict = create_template_data(locale, 'weekly', date,self.request)
    self.response.headers["Cache-Control"]="public; max-age=300;"
    return self.template('ranking_weekly.html', template_dict)  
        
class CurrentMonthHandler(helipad.Handler):
  def get(self,locale):        
    date = gmt_today()
    template_dict = create_template_data(locale, 'monthly', date,self.request)
    self.response.headers["Cache-Control"]="public; max-age=300;"
    return self.template('ranking_monthly.html', template_dict)   
  
class NotFoundHandler(helipad.Handler):
  def get(self):
    self.response.out.write("Page not found")
  
class BucketHandler(helipad.Handler):
  def get(self):
    logging.info('Bucket get called')
    self.response.out.write('Bucket get called')

  def post(self):
    data = self.request.get('data')
    timeout_ms = 100
    while True:      
      try:
        taskqueue.add(url='/taskworker/bucket/', params={'data': data})
        break      
      except taskqueue.TransientError:
        time.sleep(timeout_ms)
        timeout_ms *= 2

class AffiliateRedirectHandler(helipad.Handler):
    pass
        
main, application = helipad.app([
  ('/',MainHandler),
  ('/([a-z]{2})/',LocaleHandler),
  ('/([a-z]{2})/day/',CurrentDayHandler),
  ('/([a-z]{2})/week/',CurrentWeekHandler),
  ('/([a-z]{2})/month/',CurrentMonthHandler),
  ('/([a-z]{2})/day/(\d{4})/(\d{2})/(\d{2})/',DayHandler),
  ('/([a-z]{2})/week/(\d{4})/(\d{2})/(\d{2})/',WeekHandler),
  ('/([a-z]{2})/month/(\d{4})/(\d{2})/',MonthHandler),
  ('/task/', BucketHandler),
  ('/.*',NotFoundHandler),

])

if __name__ == '__main__':
  main()
