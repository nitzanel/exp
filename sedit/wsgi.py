import sys

# path to project folder
project_path = '/home/sedit'
if project_path not in sys.path:
	sys.path = [project_path] + sys.path

from flask_app import app as application
