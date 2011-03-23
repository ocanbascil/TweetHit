import logging
from config import *
import cachepy
from tweethit.utils.time_util import gmt_now
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb

QUERY_PREFIX = 'query|'
TEMPLATE_PREFIX = 'template|'

def serialize(models):
    '''Improve memcache performance converting to protobuf'''
    if models is None:
         return None
    elif isinstance(models, db.Model):
        # Just one instance
        return db.model_to_protobuf(models).Encode()
    else:
         # A list
         return [db.model_to_protobuf(x).Encode() for x in models]

def deserialize(data):
    '''Improve memcache performance by converting from protobuf'''
    if data is None:
        return None
    elif isinstance(data, str):
        # Just one instance
        return db.model_from_protobuf(entity_pb.EntityProto(data))
    else:
        return [db.model_from_protobuf(entity_pb.EntityProto(x)) for x in data]    
    
def run_query(cache_key,expiry,query, **kwds):
    cache_key = QUERY_PREFIX+cache_key
    results_proto = cachepy.get(cache_key)
    if results_proto is None:
        results_proto = memcache.get(cache_key)
        if results_proto is None:
            query.bind(**kwds)
            results = query.fetch(TEMPLATE_PRODUCT_COUNT)           
            #No caching between 00:00 - 01:00 (renderers are fetched and updated)   
            if gmt_now().hour != 0: 
                memcache.set(cache_key,serialize(results),expiry)
                cachepy.set(cache_key,serialize(results),expiry)
            return results
        else:
            cachepy.set(cache_key,results_proto,expiry)
    
    results = deserialize(results_proto)
    return results 

def get_template(cache_key):
    pass
