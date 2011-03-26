#DEBUG_MODE = True
import os

DEBUG_MODE = True if os.environ.get('SERVER_SOFTWARE').startswith('Devel') else False

'''Counter Write Filters'''
PRODUCT_COUNTER_MIN_COUNT = 5
USER_COUNTER_MIN_COUNT = 15

"Template Limits"
TEMPLATE_PRODUCT_COUNT = 100

'''Product ban filter limit'''
MAX_PRODUCT_INFO_RETRIES = 5

'''User ban filter limit'''
SPAM_COUNT_LIMIT = 30