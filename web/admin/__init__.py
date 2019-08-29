# -*- coding: utf-8 -*-
"""
    web.admin
    ~~~~~~~~~~~~

    This is the new admin interface for mediaTUM.
    It is implemented as a Flask app using flask-admin.

    this package is part of mediatum - a multimedia content repository
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import os
import flask_login as _flask_login
import functools as _functools
import random as _random
import string as _string
from flask import Flask, request, session, url_for, redirect, flash
from flask_admin import Admin
from flask_admin.form import SecureForm
from web.admin.views.user import UserView, UserGroupView, AuthenticatorInfoView, OAuthUserCredentialsView
from wtforms import form, fields, validators
from wtforms.validators import ValidationError
from core import db, User, config
from core.auth import authenticate_user_credentials, logout_user
from flask_admin import AdminIndexView
from flask_admin import helpers, expose
from web.admin.views.node import NodeView, FileView, NodeAliasView
from web.admin.views.setting import SettingView
from web.admin.views.acl import AccessRulesetView, AccessRuleView, AccessRulesetToRuleView
from datetime import timedelta
from werkzeug.datastructures import ImmutableDict as _ImmutableDict
from werkzeug.utils import cached_property as _cached_property
from core.templating import PyJadeExtension as _PyJadeExtension
from jinja2.loaders import FileSystemLoader as _FileSystemLoader, ChoiceLoader as _ChoiceLoader


q = db.query
DEBUG = True


class MediatumFlask(Flask):

    jinja_options = _ImmutableDict(
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_', _PyJadeExtension]
    )

    def __init__(self, import_name, template_folder="web/templates"):
        super(MediatumFlask, self).__init__(import_name=import_name, template_folder=template_folder)

    @_cached_property
    def jinja_loader(self):
        if self.template_folder is not None:
            loaders = [_FileSystemLoader(os.path.join(self.root_path, self.template_folder))]
        else:
            loaders = []
        return _ChoiceLoader(loaders)

    def add_template_loader(self, loader, pos=None):
        if pos is not None:
            self.jinja_loader.loaders.insert(pos, loader)
        else:
            self.jinja_loader.loaders.append(loader)

    def add_template_globals(self, **global_names):
        self.jinja_env.globals.update(global_names)


class IndexView(AdminIndexView):
    """Creates index view class for handling login."""

    @expose('/')
    def index(self):
        if not _flask_login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(IndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        login_form = LoginForm(request.form)

        if helpers.validate_form_on_submit(login_form):
            user = login_form.get_user()
            _flask_login.login_user(user)
        if _flask_login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        self._template_args['form'] = login_form
        return super(IndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        user = _flask_login.current_user
        logout_user(user, request)
        _flask_login.logout_user()
        return redirect(url_for('.index'))


class LoginForm(form.Form):
    class Meta(SecureForm.Meta):
        csrf_time_limit = timedelta(seconds=int(config.get('csrf.timeout', "7200")))

        @property
        def csrf_context(self):
            return session

    """Creates login form for flask-Login."""
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()
        if user is None:
            raise validators.ValidationError('Invalid user')
        if authenticate_user_credentials(self.login.data, self.password.data, request) is None:
            raise validators.ValidationError('Invalid password')
        flash('Logged in successfully')

    def validate_csrf_token(self, field):
        try:
            self._csrf.validate_csrf_token(self._csrf, field)
        except ValidationError as e:
            if (e.message == "CSRF token expired"):
                self.csrf_token.current_token = self._csrf.generate_csrf_token(field)
                csrf_errors = self.errors['csrf_token']
                csrf_errors.remove("CSRF token expired")
                if not any(csrf_errors):
                    self.errors.pop("csrf_token")

    def get_user(self):
        return q(User).filter_by(login_name=self.login.data).first()


def make_app():
    """Creates the mediaTUM-admin Flask app.
    When more parts of mediaTUM are converted to Flask,
    we might use a "global" app to which the admin interface is added.
    """
    admin_app = MediatumFlask("mediaTUM admin", template_folder="web/templates")
    admin_app.debug = True
    # Generate seed for signed session cookies
    make_key_char = _functools.partial(_random.SystemRandom().choice, _string.ascii_letters)
    admin_app.config["SECRET_KEY"] = "".join(make_key_char() for _ in xrange(80))
    admin_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(int(config.get('flask.timeout', "7200")))

    if DEBUG:
        admin_app.debug = True
        from werkzeug.debug import DebuggedApplication
        admin_app.wsgi_app = DebuggedApplication(admin_app.wsgi_app, True)

    admin = Admin(admin_app, name="mediaTUM", template_mode="bootstrap3",
                  index_view=IndexView(), base_template='admin_base.html')

    admin_enabled = config.getboolean("admin.activate", True)
    if admin_enabled:
        admin.add_view(UserView())
        admin.add_view(UserGroupView())
        admin.add_view(AuthenticatorInfoView())
        admin.add_view(OAuthUserCredentialsView())

        admin.add_view(NodeView())
        admin.add_view(FileView())
        admin.add_view(NodeAliasView())

        admin.add_view(SettingView())

        admin.add_view(AccessRuleView())
        admin.add_view(AccessRulesetView())
        admin.add_view(AccessRulesetToRuleView())

    return admin_app


app = make_app()


@app.after_request
def request_finished_db_session(response):
    from core import db
    db.session.close()
    return response


def init_login():
    """Initializes flask-login."""
    login_manager = _flask_login.LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return q(User).get(user_id)


init_login()
