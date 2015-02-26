from __future__ import absolute_import, division, print_function, unicode_literals
from flask.ext.wtf import Form
from flask.ext.login import current_user
import boto
from cgi import escape
from wtforms import StringField, BooleanField, SelectField, SubmitField, TextField, IntegerField, DateField
from wtforms.compat import text_type
from wtforms.validators import Required, Length, Email, Optional, NumberRange
from wtforms.widgets import TextArea, HTMLString
from wtforms import ValidationError
from ..models import Role, User

class EditProfileForm(Form):
    name = StringField('Real Name', validators=[Length(0, 64)])
    aws_access_key = StringField('AWS Access Key', validators=[Optional(), Length(20, 20)])
    aws_secret_key = StringField('AWS Secret Key', validators=[Optional(), Length(40, 40)])
    submit = SubmitField('Submit')

    def validate(self):
        if not super(EditProfileForm, self).validate():
            return False

        print("test")
        if self.aws_access_key.data != current_user.aws_access_key or \
                self.aws_secret_key.data != current_user.aws_secret_key:
            print("test2")
            if self.aws_access_key.data and self.aws_secret_key.data:
                try:
                    boto.connect_s3(self.aws_access_key.data, self.aws_secret_key.data).get_canonical_user_id()
                except Exception as e:
                    self.aws_access_key.errors.append('Could not connect to S3 using specified credentials')
                    return False

        return True


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real Name', validators=[Length(0, 64)])
    aws_access_key = StringField('AWS Access Key', validators=[Optional(), Length(20, 20)])
    aws_secret_key = StringField('AWS Secret Key', validators=[Optional(), Length(40, 40)])
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate(self):
        if not super(EditProfileAdminForm, self).validate():
            return False

        if self.aws_access_key.data != self.user.aws_access_key or \
                self.aws_secret_key.data != self.user.aws_secret_key:
            if self.aws_access_key.data and self.aws_secret_key.data:
                try:
                    boto.connect_s3(self.aws_access_key.data, self.aws_secret_key.data).get_canonical_user_id()
                except Exception as e:
                    self.aws_access_key.errors.append("Could not connect to S3 using specified credentials")
                    return False

        return True

class AceEditorWidget(TextArea):
    """ Renders an ACE code editor. """
    def __call__(self, field, **kwargs): 
        kwargs.setdefault('id', field.id)
        html = """
            <div id="{el_id}" style="height:500px;">{contents}</div>
            <textarea id="{el_id}_ace" name="{form_name}" style="display:none"></textarea>
        """.format(
            el_id=kwargs.get('id', field.id),
            contents=escape(text_type(field._value())),
            form_name=field.id
        )
        return HTMLString(html)

class AceEditorField(TextField):
    """ An ACE code editor field to place in a wtforms form. """
    widget = AceEditorWidget()

DEFAULT_JOB = """#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

INPUT_DATA = "s3://bucket/"

PIP_REQUIREMENTS = []

def MAP_FUNC(file_name):
    \"""
    takes local filename to be processed for your smr job
    Each line that it prints to STDOUT will be sent to REDUCE_FUNC as an argument
    \"""
    with open(file_name) as f:
        pass

def REDUCE_FUNC(line):
    \"""
    takes each line that MAP_FUNC outputs to STDOUT
    all STDOUT output of this function will be in the final job output
    \"""
    pass

def OUTPUT_RESULTS_FUNC():
    \"""
    runs when the job is done
    all STDOUT output of this function will be in the final job output
    \"""
    pass
"""

class JobEditForm(Form):
    name = StringField("Job Name", validators=[Required(), Length(1, 64)])
    body = AceEditorField("Job Definition", validators=[Required()], default=DEFAULT_JOB)
    submit = SubmitField("Submit")


class JobRunForm(Form):
    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
    date_range = IntegerField("Date Range", validators=[Optional(), NumberRange(0)])
    submit = SubmitField("Run")

class JobRunEC2Form(JobRunForm):
    pass