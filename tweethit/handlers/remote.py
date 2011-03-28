import helipad
import logging
import pythonloader
from PerformanceEngine import pdb
from tweethit.model import *
from google.appengine.api import memcache

QUERY_STRING = "SELECT __key__ FROM "

helipad.root('tweethit').template_root('static/templates/')

class DeleteHandler(helipad.Handler):
  def get(self,model_name):
    if model_name == 'memcache':
        if memcache.flush_all():
            self.response.out.write('MEMCACHE FLUSHED')
            
    elif model_name == 'template':
        pythonloader.mydata = {}
        self.response.out.write('LOCAL TEMPLATE CACHE FLUSHED')
        
    else:
        query = db.GqlQuery(QUERY_STRING+model_name)  
        keys = []
        for key in query:
            keys.append(key)
        pdb.delete(keys)
        self.response.out.write("Deleted all models of kind: %s" % model_name)
            
class DeleteKeyHandler(helipad.Handler):
  def get(self,model_name,key_name):
    if model_name == 'memcache':
      if memcache.delete(key_name):
        self.response.out.write('% with key name %s deleted from memcache')
        
    else:
      key = db.Key.from_path(model_name,key_name)
      db.delete(key)
      self.response.out.write("Deleted %s with key_name: %s" %(model_name,key_name))

class BannedUsers(helipad.Handler):
  def get(self):
    users = TwitterUser.all().fetch(10000)

    return self.template('banned_model.html', {
      'users': users,
    })
      
  def post(self):
    users = self.request.get('users').split('\n')
    
    db_targets = []
    for user_key in users:
      db_targets.append(TwitterUser(key_name = user_key.strip()))
    
    db.put(db_targets)
    TwitterUser.update_banlist(users)
    logging.info('Added banned users')
                
main, application = helipad.app({
    '/remote/delete/(\w+)/': DeleteHandler,
    '/remote/delete/(\w+)/(\w+)/': DeleteKeyHandler,
    '/remote/bannedusers/':BannedUsers,
})

if __name__ == '__main__':
    main()