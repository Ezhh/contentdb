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


from app import app, pages
from flask import *
from flask_user import *
from flask_login import login_user, logout_user
from app.models import *
import flask_menu as menu
from flask.ext import markdown
from sqlalchemy import func
from werkzeug.contrib.cache import SimpleCache
from urllib.parse import urlparse
cache = SimpleCache()

@app.template_filter()
def domain(url):
	return urlparse(url).netloc

# Use nginx to serve files on production instead
@app.route("/static/<path:path>")
def send_static(path):
	return send_from_directory("public/static", path)

@app.route("/uploads/<path:path>")
def send_upload(path):
	return send_from_directory("public/uploads", path)

@app.route("/")
@menu.register_menu(app, ".", "Home")
def home_page():
	packages = Package.query.filter_by(approved=True).all()
	return render_template("index.html", packages=packages)

from . import users, githublogin, packages, sass, tasks, admin, notifications

@menu.register_menu(app, ".help", "Help", order=19, endpoint_arguments_constructor=lambda: { 'path': 'help' })
@app.route('/<path:path>/')
def flatpage(path):
    page = pages.get_or_404(path)
    template = page.meta.get('template', 'flatpage.html')
    return render_template(template, page=page)
