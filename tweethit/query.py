from google.appengine.ext.db import GqlQuery
from tweethit.model import ProductCounter

'''Returns top rankings for a given frequency and time period
Daily frequency will be used to calculate other frequencies'''

TOP_PRODUCT_COUNTERS = GqlQuery('SELECT * FROM ProductCounter WHERE \
                                            store =:store \
                                            AND frequency = :frequency \
                                            AND is_banned = False \
                                            ORDER BY count DESC')

DAILY_TOP_COUNTERS = GqlQuery('SELECT * FROM ProductCounter WHERE \
                                            store =:store \
                                            AND day = :day\
                                            AND is_banned = False \
                                            ORDER BY count DESC')