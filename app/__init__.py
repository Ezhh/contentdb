# Content DB
# Copyright (C) 2018  rubenwardy
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from flask import *
from flask_user import *
import flask_menu as menu
from flask_mail import Mail
from flask.ext import markdown
from flask_github import GitHub
from flask_wtf.csrf import CsrfProtect
from flask_flatpages import FlatPages
import os

app = Flask(__name__)
app.config["FLATPAGES_ROOT"] = "flatpages"
app.config["FLATPAGES_EXTENSION"] = ".md"
app.config.from_pyfile(os.environ["FLASK_CONFIG"])

menu.Menu(app=app)
markdown.Markdown(app, extensions=["fenced_code"], safe_mode=True, output_format="html5")
github = GitHub(app)
csrf = CsrfProtect(app)
mail = Mail(app)
pages = FlatPages(app)

from . import models, tasks
from .views import *
