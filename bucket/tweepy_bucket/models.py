try:
    import cPickle as pickle
except ImportError:
    import pickle
    
class SimpleStatus(object):
    
    def __init__(self,status):
        self.text = status.text
        self.user_id = status.author.id
        self.screen_name = status.author.screen_name
        
class SimpleUrl(dict):
    
    def __init__(self,url,author):
        self['url'] = url
        self['user_id'] = author.id
        #self['screen_name'] = author.screen_name
    
class BanList(object):

    def __init__(self,file_path = None):
        print 'BanList initializing'
        if file_path is None:
            print 'Creating empty filter'
            self.ban_list = set()
            return
        
        print 'BanList initializing'
        print 'Opening file'
        file = open(file_path,'r')
        print 'Creating ban filter'
        array = [line for line in file]
        self.ban_list = set(map(lambda line: line.rstrip(), array))
        print 'Created ban filter with %s elements' %len(self.ban_list)


    def check_ban(self,user_id):
        if str(user_id) in self.ban_list:
            return True
        else:
            return False    


class Bucket(object):
    def __init__(self,bucket_size = 1000):
        self.bucket_size = bucket_size
        self._items = []
        self.is_full = False
        
    def get_items(self):
        return self._items
    
    def set_items(self,val):
        pass
        
    def add_item(self,status):
        self._items.append(status)
        if len(self._items) == self.bucket_size:
            self.is_full = True
        
    def pour(self):
        print "Pouring bucket with length %d" % len(self._items)
        
        seq = self._items[0:self.bucket_size]
        
        del self._items[0:self.bucket_size]
        self.is_full = False
        return repr(seq)
        
        
    def test_arr(self):
        arr = ['a','b','c','d','e']
        return pickle.dumps(arr)
    items = property(get_items,set_items)
