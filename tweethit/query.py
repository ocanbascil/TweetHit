from google.appengine.ext.db import GqlQuery
from tweethit.model import ProductCounter

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