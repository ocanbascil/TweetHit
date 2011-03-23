# This file is part of helipad (http://github.com/jgeewax/helipad).
# 
# Copyright (C) 2010 JJ Geewax http://geewax.org/
# All rights reserved.
# 
# This software is licensed as described in the file COPYING.txt,
# which you should have received as part of this distribution.

# ==============================================================================
# Imports
# ==============================================================================
from __future__ import with_statement
import inspect
import os
import sys
import mimetypes
from  pythonloader import PythonLoader
from google.appengine.ext import webapp

# ==============================================================================
# Exports
# ==============================================================================
__all__ = ['json', 'Handler', 'root', 'app', 'static']

# ==============================================================================
# Convenience imports
# ==============================================================================
from django.utils import simplejson as json

# ==============================================================================
# Private globals
# ==============================================================================
_ROOT_MODULE = None
_TEMPLATE_ROOT = None

# ==============================================================================
# Set up zipimports
# ==============================================================================
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jinja2'))

# ==============================================================================
# Classes
# ==============================================================================

class Handler(webapp.RequestHandler):
  def static(self, path):
    file_name = os.path.join(os.path.dirname(root().__file__), path)
    
    # Try to guess the content type:
    type, _ = mimetypes.guess_type(file_name)
    if type:
      self.response.headers['Content-Type'] = type
    
    # Write the file to the output stream
    with open(file_name, 'r') as f:
      for line in f:
        self.response.out.write(line)
  
  def render(self, path, params=None):
    env = self._get_template_environment()
    template = env.get_template(path)
    return template.render(params or {})
  
  def template(self, path, params=None):
    self.response.out.write(self.render(path, params))
  
  @classmethod
  def _get_template_environment(cls):
    if not template_root():
      raise ValueError, "Template root not set."
    
    from jinja2 import Environment, FileSystemLoader
    
    return Environment(loader=FileSystemLoader(
      os.path.join(os.path.dirname(root().__file__), template_root())
    ))

class Application(object):
  def __init__(self, *args, **kwargs):
    self.url_mapping = self._get_url_mapping(*args, **kwargs)
    self.application = self.get_application(self.url_mapping)
    self.main = self.get_main_method(self.application)
  
  @classmethod
  def get_application(cls, url_mapping):
    return webapp.WSGIApplication(url_mapping)
  
  @classmethod
  def get_main_method(cls, application):
    def main():
      from google.appengine.ext.webapp.util import run_wsgi_app
      run_wsgi_app(application)
    return main
  
  @classmethod
  def _get_url_mapping(cls, *args):
    prefix, mapping = cls._get_prefix_and_mapping(args)
    
    # If there is just one Handler, bind it to any URL
    if inspect.isclass(mapping) and issubclass(mapping, webapp.RequestHandler):
      return [('.*', mapping)]
    
    # A dictionary of {'/route/': Handler, ...}
    elif isinstance(mapping, dict):
      return cls._get_url_mapping(prefix, mapping.items())
    
    # A list of tuples of [('/route/', Handler), ...]
    elif isinstance(mapping, (list, tuple)):
      mappings = list(mapping)
      if prefix:
        for i, item in enumerate(mappings):
          mappings[i] = (prefix + item[0], item[1])
      return mappings
    
    raise ValueError, "Invalid arguments: %s" % args
  
  @classmethod
  def _get_prefix_and_mapping(cls, args):
    if len(args) == 1:
      return None, args[0]
    elif len(args) == 2:
      return args
    
    raise ValueError, "Invalid arguments: %s" % args

class StaticApplication(Application):
  @classmethod
  def _get_url_mapping(cls, *args):
    prefix, mapping = cls._get_prefix_and_mapping(args)
    
    # If there is just one string, bind it to any URL
    if isinstance(mapping, basestring):
      return [('.*', cls._get_static_handler(mapping))]
    
    # A dictionary of {'/route/': '/path/to/file.html', ...}
    elif isinstance(mapping, dict):
      return cls._get_url_mapping(prefix, mapping.items())
    
    # A list of tuples of [('/route/', '/path/to/file.html'), ...]
    elif isinstance(mapping, (list, tuple)):
      mappings = list(mapping)
      for i, item in enumerate(mappings):
        mappings[i] = (item[0], cls._get_static_handler(item[1]))
      
      return super(StaticApplication, cls)._get_url_mapping(prefix, mappings)
    
    raise ValueError, "Invalid arguments: %s" % args
  
  @classmethod
  def _get_static_handler(cls, path):
    class StaticHandler(Handler):
      def get(self):
        self.static(path)
    return StaticHandler

# ==============================================================================
# Functions
# ==============================================================================

def root(module=None):
  """
  Sets the "root module" for helipad.
  
  The root module's directory is used as the definition of where relative paths
  are based off of.
  """
  global _ROOT_MODULE
  
  if module is None:
    return _ROOT_MODULE
  
  if isinstance(module, basestring):
    components = module.split('.')
    module = __import__(module, globals(), locals(), [], -1)
    
    for component in components[1:]:
      module = getattr(module, component)
  
  if inspect.ismodule(module):
    _ROOT_MODULE = module
  else:
    raise ValueError, "Invalid module: %s" % module
  
  # Return a reference to this module (so that we can string together method calls)
  return __import__('helipad', globals(), locals(), [], -1)

def template_root(directory=None):
  global _TEMPLATE_ROOT
  
  if directory is None:
    return _TEMPLATE_ROOT
  
  _TEMPLATE_ROOT = directory
  
  # Return a reference to this module (so that we can string together method calls)
  return __import__('helipad', globals(), locals(), [], -1)

def app(*args, **kwargs):
  app = Application(*args, **kwargs)
  return app.main, app.application

def static(*args, **kwargs):
  app = StaticApplication(*args, **kwargs)
  return app.main, app.application
