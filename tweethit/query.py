from google.appengine.ext.db import GqlQuery
from tweethit.model import ProductCounter,DAILY,WEEKLY,MONTHLY

'''Returns top rankings for a given frequency and time period
Daily frequency will be used to calculate other frequencies'''

DAILY_TOP_COUNTERS = GqlQuery('SELECT * FROM ProductCounter WHERE \
                                            store =:store \
                                            AND day = :day\
                                            AND is_banned = False \
                                            ORDER BY count DESC')

WEEKLY_TOP_COUNTERS = GqlQuery('SELECT * FROM ProductCounter WHERE \
                                            store =:store \
                                            AND week = :week\
                                            AND year = :year\
                                            AND is_banned = False \
                                            ORDER BY count DESC')

MONTHLY_TOP_COUNTERS =  GqlQuery('SELECT * FROM ProductCounter WHERE \
                                            store =:store \
                                            AND month = :month\
                                            AND year = :year\
                                            AND is_banned = False \
                                            ORDER BY count DESC')

def get_counter_query_for_frequency(frequency,date,store_key):
  if frequency == DAILY:
    query = DAILY_TOP_COUNTERS
    query.bind(store = store_key,day = date)
  elif frequency == WEEKLY:
    query = WEEKLY_TOP_COUNTERS
    query.bind(store = store_key, week = date.isocalendar()[1],year = date.year)
  elif frequency == MONTHLY:
    query = MONTHLY_TOP_COUNTERS 
    query.bind(store = store_key, month = date.month,year = date.year)
    
  return query

DAILY_RENDERERS = GqlQuery('SELECT * FROM ProductRenderer WHERE \
                                            store =:store \
                                            AND day = :day\
                                            AND is_banned = False \
                                            ORDER BY count DESC')

WEEKLY_RENDERERS = GqlQuery('SELECT * FROM ProductRenderer WHERE \
                                            store =:store \
                                            AND week = :week\
                                            AND year = :year\
                                            AND is_banned = False \
                                            ORDER BY count DESC')

MONTHLY_RENDERERS = GqlQuery('SELECT * FROM ProductRenderer WHERE \
                                            store =:store \
                                            AND month = :month\
                                            AND year = :year\
                                            AND is_banned = False \
                                            ORDER BY count DESC')

def get_renderer_query_for_frequency(frequency,date,store_key):
  if frequency == DAILY:
    query = DAILY_RENDERERS
    query.bind(store = store_key,day = date)
  elif frequency == WEEKLY:
    query = WEEKLY_RENDERERS
    query.bind(store = store_key, week = date.isocalendar()[1],year = date.year)
  elif frequency == MONTHLY:
    query = MONTHLY_RENDERERS 
    query.bind(store = store_key, month = date.month,year = date.year)
  return query

USER_COUNTER_CLEANUP_TARGETS = GqlQuery('SELECT __key__ FROM UserCounter')