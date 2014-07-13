from __future__ import absolute_import, division, print_function, unicode_literals
from flask import render_template, redirect, url_for, abort, flash, request, current_app
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, JobForm
from .. import db
from ..models import Permission, Role, User, Job
from ..decorators import admin_required


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['SMR_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: {}\nParameters: {}\nDuration: {}s\nContext: {}\n'.format(
                query.statement, query.parameters, query.duration, query.context))
    return response


@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    pagination = current_user.jobs.order_by(Job.timestamp.desc()).paginate(
        page, per_page=current_app.config['SMR_JOBS_PER_PAGE'],
        error_out=False)
    jobs = pagination.items
    return render_template('index.html', jobs=jobs, pagination=pagination)


@main.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.aws_access_key = form.aws_access_key.data
        current_user.aws_secret_key = form.aws_secret_key.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', id=current_user.id))
    form.name.data = current_user.name
    form.aws_access_key.data = current_user.aws_access_key
    form.aws_secret_key.data = current_user.aws_secret_key
    return render_template('user_edit.html', form=form)


@main.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.aws_access_key = form.aws_access_key.data
        user.aws_secret_key = form.aws_secret_key.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', id=user.id))
    form.email.data = user.email
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    return render_template('user_edit.html', form=form, user=user)


@main.route('/job/create', methods=['GET', 'POST'])
@login_required
def job_create():
    form = JobForm()
    if current_user.can(Permission.CREATE_JOBS) and \
            form.validate_on_submit():
        job = Job(name=form.name.data,
                  body=form.body.data,
                  author=current_user._get_current_object())
        db.session.add(job)
        return redirect(url_for('.index'))
    return render_template('job_edit.html', form=form)


@main.route('/job/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    job = Job.query.get_or_404(id)
    if current_user != job.author and \
            not current_user.can(Permission.ADMINISTER):
        # not 403 because we don't want to tell user that job exists
        abort(404) # not 403 because we don't want to tell 
    form = JobForm()
    if form.validate_on_submit():
        job.name = form.name.data
        job.body = form.body.data
        db.session.add(job)
        flash('The job has been updated.')
        return redirect(url_for('.job', id=job.id))
    form.name.data = job.name
    form.body.data = job.body
    return render_template('job_edit.html', form=form)
