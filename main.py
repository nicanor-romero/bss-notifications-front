import flask
import pytz
import os
import logging
import commons
import datetime
import db_manager as m_db_manager
from functools import wraps


app = flask.Flask(__name__)
local_tz = pytz.timezone('America/Argentina/Cordoba')

STATUS_PENDING_APPROVAL = 'STATUS_PENDING_APPROVAL'
STATUS_PENDING_DISPATCH = 'STATUS_PENDING_DISPATCH'
STATUS_SENT = 'STATUS_SENT'
STATUS_CANCELLED = 'STATUS_CANCELLED'
STATUS_EXPIRED = 'STATUS_EXPIRED'

statuses = [
    STATUS_PENDING_APPROVAL,
    STATUS_PENDING_DISPATCH,
    STATUS_SENT,
    STATUS_CANCELLED,
    STATUS_EXPIRED
]

# check_if_logged_in returns True/False and a render_template call in case the user is not logged in
def check_if_logged_in(func):
    @wraps(func)
    def _check_if_logged_in(*args, **kwargs):
        if "username" not in flask.session:
            return flask.render_template('login.html')
        return func(*args, **kwargs)
    return _check_if_logged_in


def global_variables():
    return {'user_name': flask.session.get('user_name')}


@app.route('/', methods=["GET"])
@check_if_logged_in
def home():
    from_date = datetime.datetime.now() - datetime.timedelta(days=20)
    to_date = datetime.datetime.now() - datetime.timedelta(days=19)
    notifications = db_manager.get_db_invoice_expiration_notifications(from_date, to_date)
    notifications = humanize_notifications(notifications)
    return flask.render_template('home.html', notifications=notifications, **global_variables())


def humanize_notifications(notifications):
    status_to_human = {
        STATUS_PENDING_APPROVAL: 'Pendiente',
        STATUS_PENDING_DISPATCH: 'Enviando...',
        STATUS_SENT: 'Enviada',
        STATUS_CANCELLED: 'Cancelada',
        STATUS_EXPIRED: 'Expirada',
    }
    for n in notifications:
        n['status_humanized'] = status_to_human.get(n.get('status'))
        n['status_icon'] = status_to_human.get(n.get('status'))
    return notifications


# Other
@app.route('/login', methods=["GET"])
def login():
    if flask.request.method == "GET":
        if "username" not in flask.session:
            return flask.render_template("login.html")
        else:
            return flask.redirect(flask.url_for("home"))


@app.route('/check-login', methods=["POST"])
def check_login():
    form_email = flask.request.form.get('username')
    form_password = flask.request.form.get('password')
    login_status = db_manager.check_user_password(form_email, form_password)
    if not login_status.get('ok', False):
        return login_status

    flask.session['username'] = login_status.get('email')
    flask.session['user_name'] = login_status.get('name')
    return {'ok': True}


@app.route('/logout', methods=["GET"])
def logout():
    flask.session.pop('username', None)
    flask.session.pop('user_name', None)
    return flask.redirect(flask.url_for("home"))


@app.route('/set-notification-status', methods=["POST"])
@check_if_logged_in
def set_notification_status_approved():
    notification_id = flask.request.form.get('notification_id')
    if notification_id is None:
        return {'ok': False}

    status = flask.request.form.get('status')
    if notification_id is None or status not in statuses:
        return {'ok': False}

    ok = db_manager.set_db_invoice_expiration_notification_status(notification_id, status)
    return {'ok': ok}


@app.errorhandler(404)
@app.route('/404', methods=['GET'])
def page_not_found(e=None):
    return flask.render_template("error_404.html", **global_variables()), 404


@app.errorhandler(500)
@app.route('/500', methods=['GET'])
def internal_server_error(e=None):
    return flask.render_template("error_500.html", **global_variables()), 500


@app.route('/terms', methods=["GET"])
def terms_of_use():
    return flask.render_template('terms_of_use.html')


@app.route('/privacy', methods=["GET"])
def privacy_policy():
    return flask.render_template('privacy_policy.html')


commons.configure_logger('bss_notifications_front')
log = logging.getLogger()
db_secrets = {
    'username': os.environ.get('DB_USERNAME'),
    'password': os.environ.get('DB_PASSWORD'),
    'fernet_key': os.environ.get('DB_SECRETS_KEY')
}
app.secret_key = os.environ.get('FLASK_SECRET_KEY', '1234567890')
app.register_error_handler(404, page_not_found)
app.register_error_handler(500, internal_server_error)

db_manager = m_db_manager.DatabaseManager(db_secrets)

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=int(os.environ.get("PORT", 8080)), ssl_context='adhoc')
