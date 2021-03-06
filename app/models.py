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


from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app import app
from datetime import datetime
from sqlalchemy.orm import validates
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter
import enum

# Initialise database
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class UserRank(enum.Enum):
	NOT_JOINED = 0
	NEW_MEMBER = 1
	MEMBER     = 2
	EDITOR     = 3
	MODERATOR  = 4
	ADMIN      = 5

	def atLeast(self, min):
		return self.value >= min.value

	def getTitle(self):
		return self.name.replace("_", " ").title()

	def toName(self):
		return self.name.lower()

	def __str__(self):
		return self.name

	@classmethod
	def choices(cls):
		return [(choice, choice.getTitle()) for choice in cls]

	@classmethod
	def coerce(cls, item):
		return item if type(item) == UserRank else UserRank[item]


class Permission(enum.Enum):
	EDIT_PACKAGE       = "EDIT_PACKAGE"
	APPROVE_CHANGES    = "APPROVE_CHANGES"
	DELETE_PACKAGE     = "DELETE_PACKAGE"
	CHANGE_AUTHOR      = "CHANGE_AUTHOR"
	MAKE_RELEASE       = "MAKE_RELEASE"
	APPROVE_RELEASE    = "APPROVE_RELEASE"
	APPROVE_NEW        = "APPROVE_NEW"
	CHANGE_RELEASE_URL = "CHANGE_RELEASE_URL"
	CHANGE_DNAME       = "CHANGE_DNAME"
	CHANGE_RANK        = "CHANGE_RANK"
	CHANGE_EMAIL       = "CHANGE_EMAIL"
	EDIT_EDITREQUEST   = "EDIT_EDITREQUEST"

	# Only return true if the permission is valid for *all* contexts
	# See Package.checkPerm for package-specific contexts
	def check(self, user):
		if not user.is_authenticated:
			return False

		if self == Permission.APPROVE_NEW or \
				self == Permission.APPROVE_CHANGES or \
				self == Permission.APPROVE_RELEASE:
			return user.rank.atLeast(UserRank.EDITOR)
		else:
			raise Exception("Non-global permission checked globally. Use Package.checkPerm or User.checkPerm instead.")


class User(db.Model, UserMixin):
	id = db.Column(db.Integer, primary_key=True)

	# User authentication information
	username = db.Column(db.String(50), nullable=False, unique=True)
	password = db.Column(db.String(255), nullable=False, server_default="")
	reset_password_token = db.Column(db.String(100), nullable=False, server_default="")

	rank = db.Column(db.Enum(UserRank))

	# Account linking
	github_username = db.Column(db.String(50), nullable=True, unique=True)
	forums_username = db.Column(db.String(50), nullable=True, unique=True)

	# User email information
	email = db.Column(db.String(255), nullable=True, unique=True)
	confirmed_at = db.Column(db.DateTime())

	# User information
	active = db.Column("is_active", db.Boolean, nullable=False, server_default="0")
	display_name = db.Column(db.String(100), nullable=False, server_default="")

	# Content
	notifications = db.relationship("Notification", primaryjoin="User.id==Notification.user_id")

	# causednotifs  = db.relationship("Notification", backref="causer", lazy="dynamic")
	packages      = db.relationship("Package", backref="author", lazy="dynamic")
	requests      = db.relationship("EditRequest", backref="author", lazy="dynamic")

	def __init__(self, username):
		import datetime

		self.username = username
		self.confirmed_at = datetime.datetime.now() - datetime.timedelta(days=6000)
		self.display_name = username
		self.rank = UserRank.NOT_JOINED

	def canAccessTodoList(self):
		return Permission.APPROVE_NEW.check(self) or \
				Permission.APPROVE_RELEASE.check(self) or \
				Permission.APPROVE_CHANGES.check(self)

	def isClaimed(self):
		return self.rank.atLeast(UserRank.NEW_MEMBER)

	def checkPerm(self, user, perm):
		if not user.is_authenticated:
			return False

		if type(perm) == str:
			perm = Permission[perm]
		elif type(perm) != Permission:
			raise Exception("Unknown permission given to User.checkPerm()")

		# Members can edit their own packages, and editors can edit any packages
		if perm == Permission.CHANGE_AUTHOR:
			return user.rank.atLeast(UserRank.EDITOR)
		elif perm == Permission.CHANGE_RANK or perm == Permission.CHANGE_DNAME:
			return user.rank.atLeast(UserRank.MODERATOR)
		elif perm == Permission.CHANGE_EMAIL:
			return user == self or (user.rank.atLeast(UserRank.MODERATOR) and user.rank.atLeast(self.rank))
		else:
			raise Exception("Permission {} is not related to users".format(perm.name))

class UserEmailVerification(db.Model):
	id      = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
	email   = db.Column(db.String(100))
	token   = db.Column(db.String(32))
	user    = db.relationship("User", foreign_keys=[user_id])

class Notification(db.Model):
	id        = db.Column(db.Integer, primary_key=True)
	user_id   = db.Column(db.Integer, db.ForeignKey("user.id"))
	causer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
	user      = db.relationship("User", foreign_keys=[user_id])
	causer    = db.relationship("User", foreign_keys=[causer_id])

	title     = db.Column(db.String(100), nullable=False)
	url       = db.Column(db.String(200), nullable=True)

	def __init__(self, us, cau, titl, ur):
		self.user   = us
		self.causer = cau
		self.title  = titl
		self.url    = ur


class License(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(50), nullable=False, unique=True)
	packages = db.relationship("Package", backref="license", lazy="dynamic")

	def __init__(self, v):
		self.name = v

	def __str__(self):
		return self.name


class PackageType(enum.Enum):
	MOD  = "Mod"
	GAME = "Game"
	TXP  = "Texture Pack"

	def toName(self):
		return self.name.lower()

	def __str__(self):
		return self.name

	@classmethod
	def choices(cls):
		return [(choice, choice.value) for choice in cls]

	@classmethod
	def coerce(cls, item):
		return item if type(item) == PackageType else PackageType[item]


class PackagePropertyKey(enum.Enum):
	name         = "Name"
	title        = "Title"
	shortDesc    = "Short Description"
	desc         = "Description"
	type         = "Type"
	license      = "License"
	tags         = "Tags"
	repo         = "Repository"
	website      = "Website"
	issueTracker = "Issue Tracker"
	forums       = "Forum Topic ID"

	def convert(self, value):
		if self == PackagePropertyKey.tags:
			return ",".join([t.title for t in value])
		else:
			return str(value)

tags = db.Table("tags",
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
    db.Column("package_id", db.Integer, db.ForeignKey("package.id"), primary_key=True)
)

harddeps = db.Table("harddeps",
	db.Column("package_id",    db.Integer, db.ForeignKey("package.id"), primary_key=True),
    db.Column("dependency_id", db.Integer, db.ForeignKey("package.id"), primary_key=True)
)

softdeps = db.Table("softdeps",
	db.Column("package_id",    db.Integer, db.ForeignKey("package.id"), primary_key=True),
    db.Column("dependency_id", db.Integer, db.ForeignKey("package.id"), primary_key=True)
)

class Package(db.Model):
	id           = db.Column(db.Integer, primary_key=True)

	# Basic details
	author_id    = db.Column(db.Integer, db.ForeignKey("user.id"))
	name         = db.Column(db.String(100), nullable=False)
	title        = db.Column(db.String(100), nullable=False)
	shortDesc    = db.Column(db.String(200), nullable=False)
	desc         = db.Column(db.Text, nullable=True)
	type         = db.Column(db.Enum(PackageType))
	created_at   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	license_id   = db.Column(db.Integer, db.ForeignKey("license.id"))

	approved     = db.Column(db.Boolean, nullable=False, default=False)

	# Downloads
	repo         = db.Column(db.String(200), nullable=True)
	website      = db.Column(db.String(200), nullable=True)
	issueTracker = db.Column(db.String(200), nullable=True)
	forums       = db.Column(db.Integer,     nullable=True)

	tags = db.relationship("Tag", secondary=tags, lazy="subquery",
			backref=db.backref("packages", lazy=True))

	harddeps = db.relationship("Package",
				secondary=harddeps,
				primaryjoin=id==harddeps.c.package_id,
				secondaryjoin=id==harddeps.c.dependency_id,
				backref="dependents")

	softdeps = db.relationship("Package",
				secondary=softdeps,
				primaryjoin=id==softdeps.c.package_id,
				secondaryjoin=id==softdeps.c.dependency_id,
				backref="softdependents")

	releases = db.relationship("PackageRelease", backref="package",
			lazy="dynamic", order_by=db.desc("package_release_releaseDate"))

	screenshots = db.relationship("PackageScreenshot", backref="package",
			lazy="dynamic")

	requests = db.relationship("EditRequest", backref="package",
			lazy="dynamic")

	def getAsDictionary(self, base_url):
		return {
			"name": self.name,
			"title": self.title,
			"author": self.author.display_name,
			"shortDesc": self.shortDesc,
			"type": self.type.toName(),
			"license": self.license.name,
			"repo": self.repo,
			"url": base_url + self.getDownloadURL(),
			"release": self.getDownloadRelease().id if self.getDownloadRelease() is not None else None,
			"screenshots": [base_url + ss.url for ss in self.screenshots]
		}

	def getDetailsURL(self):
		return url_for("package_page",
				author=self.author.username, name=self.name)

	def getEditURL(self):
		return url_for("create_edit_package_page",
				author=self.author.username, name=self.name)

	def getApproveURL(self):
		return url_for("approve_package_page",
				author=self.author.username, name=self.name)

	def getNewScreenshotURL(self):
		return url_for("create_screenshot_page",
				author=self.author.username, name=self.name)

	def getCreateReleaseURL(self):
		return url_for("create_release_page",
				author=self.author.username, name=self.name)

	def getCreateEditRequestURL(self):
		return url_for("create_edit_editrequest_page",
				author=self.author.username, name=self.name)

	def getDownloadURL(self):
		return url_for("package_download_page",
				author=self.author.username, name=self.name)

	def getMainScreenshotURL(self):
		screenshot = self.screenshots.first()
		return screenshot.url if screenshot is not None else None

	def getDownloadRelease(self):
		for rel in self.releases:
			if rel.approved:
				return rel

		return None

	def checkPerm(self, user, perm):
		if not user.is_authenticated:
			return False

		if type(perm) == str:
			perm = Permission[perm]
		elif type(perm) != Permission:
			raise Exception("Unknown permission given to Package.checkPerm()")

		isOwner = user == self.author

		# Members can edit their own packages, and editors can edit any packages
		if perm == Permission.MAKE_RELEASE:
			return isOwner or user.rank.atLeast(UserRank.EDITOR)

		if perm == Permission.EDIT_PACKAGE or perm == Permission.APPROVE_CHANGES:
			return user.rank.atLeast(UserRank.MEMBER if isOwner else UserRank.EDITOR)

		# Editors can change authors, approve new packages, and approve releases
		elif perm == Permission.CHANGE_AUTHOR or perm == Permission.APPROVE_NEW \
				or perm == Permission.APPROVE_RELEASE:
			return user.rank.atLeast(UserRank.EDITOR)

		# Moderators can delete packages
		elif perm == Permission.DELETE_PACKAGE or perm == Permission.CHANGE_RELEASE_URL:
			return user.rank.atLeast(UserRank.MODERATOR)

		else:
			raise Exception("Permission {} is not related to packages".format(perm.name))

class Tag(db.Model):
	id              = db.Column(db.Integer,    primary_key=True)
	name            = db.Column(db.String(100), unique=True, nullable=False)
	title           = db.Column(db.String(100), nullable=False)
	backgroundColor = db.Column(db.String(6),   nullable=False)
	textColor       = db.Column(db.String(6),   nullable=False)

	def __init__(self, title, backgroundColor="000000", textColor="ffffff"):
		self.title           = title
		self.backgroundColor = backgroundColor
		self.textColor       = textColor

		import re
		regex = re.compile("[^a-z_]")
		self.name = regex.sub("", self.title.lower().replace(" ", "_"))

class PackageRelease(db.Model):
	id           = db.Column(db.Integer, primary_key=True)

	package_id   = db.Column(db.Integer, db.ForeignKey("package.id"))
	title        = db.Column(db.String(100), nullable=False)
	releaseDate  = db.Column(db.DateTime,        nullable=False)
	url          = db.Column(db.String(200), nullable=False)
	approved     = db.Column(db.Boolean, nullable=False, default=False)
	task_id      = db.Column(db.String(37), nullable=True)


	def getEditURL(self):
		return url_for("edit_release_page",
				author=self.package.author.username,
				name=self.package.name,
				id=self.id)

	def __init__(self):
		self.releaseDate = datetime.now()

class PackageScreenshot(db.Model):
	id         = db.Column(db.Integer, primary_key=True)
	package_id = db.Column(db.Integer, db.ForeignKey("package.id"))
	title      = db.Column(db.String(100), nullable=False)
	url        = db.Column(db.String(100), nullable=False)

	def getThumbnailURL(self):
		return self.url  # TODO

class EditRequest(db.Model):
	id           = db.Column(db.Integer, primary_key=True)

	package_id   = db.Column(db.Integer, db.ForeignKey("package.id"))
	author_id    = db.Column(db.Integer, db.ForeignKey("user.id"))

	title        = db.Column(db.String(100), nullable=False)
	desc         = db.Column(db.String(1000), nullable=True)

	# 0 - open
	# 1 - merged
	# 2 - rejected
	status       = db.Column(db.Integer, nullable=False, default=0)

	changes = db.relationship("EditRequestChange", backref="request",
			lazy="dynamic")

	def getURL(self):
		return url_for("view_editrequest_page",
				author=self.package.author.username,
				name=self.package.name,
				id=self.id)

	def getApproveURL(self):
		return url_for("approve_editrequest_page",
				author=self.package.author.username,
				name=self.package.name,
				id=self.id)

	def getRejectURL(self):
		return url_for("reject_editrequest_page",
				author=self.package.author.username,
				name=self.package.name,
				id=self.id)

	def getEditURL(self):
		return url_for("create_edit_editrequest_page",
				author=self.package.author.username,
				name=self.package.name,
				id=self.id)

	def applyAll(self, package):
		for change in self.changes:
			change.apply(package)


	def checkPerm(self, user, perm):
		if not user.is_authenticated:
			return False

		if type(perm) == str:
			perm = Permission[perm]
		elif type(perm) != Permission:
			raise Exception("Unknown permission given to EditRequest.checkPerm()")

		isOwner = user == self.author

		# Members can edit their own packages, and editors can edit any packages
		if perm == Permission.EDIT_EDITREQUEST:
			return isOwner or user.rank.atLeast(UserRank.EDITOR)

		else:
			raise Exception("Permission {} is not related to packages".format(perm.name))




class EditRequestChange(db.Model):
	id           = db.Column(db.Integer, primary_key=True)

	request_id   = db.Column(db.Integer, db.ForeignKey("edit_request.id"))
	key          = db.Column(db.Enum(PackagePropertyKey), nullable=False)

	# TODO: make diff instead
	oldValue     = db.Column(db.Text, nullable=True)
	newValue     = db.Column(db.Text, nullable=True)

	def apply(self, package):
		if self.key == PackagePropertyKey.tags:
			package.tags.clear()
			for tagTitle in self.newValue.split(","):
				tag = Tag.query.filter_by(title=tagTitle.strip()).first()
				package.tags.append(tag)
		else:
			setattr(package, self.key.name, self.newValue)

# Setup Flask-User
db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
user_manager = UserManager(db_adapter, app)     # Initialize Flask-User
