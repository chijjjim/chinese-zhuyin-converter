import sys
sys.path.insert(0, '/var/www/html/bpmf/backend')

from app import create_app
application = create_app()