from __future__ import absolute_import, division, print_function, unicode_literals
from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import views
