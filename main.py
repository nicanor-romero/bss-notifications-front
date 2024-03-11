import flask
import pytz
import os
import logging
import commons
import datetime
import hashlib
import hmac
import db_manager as m_db_manager
from functools import wraps


app = flask.Flask(__name__)
local_tz = pytz.timezone('America/Argentina/Cordoba')

STATUS_PENDING_APPROVAL = 'STATUS_PENDING_APPROVAL'
STATUS_PENDING_DISPATCH = 'STATUS_PENDING_DISPATCH'
STATUS_SENT = 'STATUS_SENT'
STATUS_DISABLED = 'STATUS_DISABLED'
STATUS_DISPATCH_ERROR = 'STATUS_DISPATCH_ERROR'
STATUS_EXPIRED = 'STATUS_EXPIRED'

status_to_human = {
    STATUS_PENDING_APPROVAL: 'Pendiente',
    STATUS_PENDING_DISPATCH: 'Enviando...',
    STATUS_SENT: 'Enviada',
    STATUS_DISABLED: 'Deshabilitada',
    STATUS_DISPATCH_ERROR: 'Error de envío',
    STATUS_EXPIRED: 'Expirada',
}

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
    from_date = datetime.datetime.combine(datetime.datetime.today() - datetime.timedelta(days=20), datetime.datetime.min.time())
    to_date = datetime.datetime.combine(datetime.datetime.today() - datetime.timedelta(days=19), datetime.datetime.min.time())
    notifications = db_manager.get_db_invoice_expiration_notifications(from_date, to_date)
    notifications = humanize_notifications(notifications)
    # Sort notifications by client name
    notifications = sorted(notifications, key=lambda n: n.client_info.name)
    return flask.render_template('home.html', notifications=notifications, **global_variables())


@app.route('/set-notification-status', methods=["POST"])
@check_if_logged_in
def set_notification_status():
    notification_id = flask.request.form.get('notification_id')
    if not notification_id:
        return {'ok': False}

    status = flask.request.form.get('status')
    if notification_id is None or status not in status_to_human:
        return {'ok': False}

    ok = db_manager.set_db_invoice_expiration_notification_status(notification_id, status)
    return {'ok': ok, 'status': status, 'status_humanized': status_to_human.get(status)}


@app.route('/whatsapp-webhook', methods=["GET", "POST"])
def whatsapp_webhook():
    if flask.request.method == "GET":
        log.debug('Got call at whatsapp_webook GET!')
        WHATSAPP_VERIFY_TOKEN = '8v34L0HH3sq0iu1fnqx2JUPJ'

        # [('hub.mode', 'subscribe'), ('hub.challenge', '1776433461'), ('hub.verify_token', '8v34L0HH3sq0iu1fnqx2JUPJ')])

        verify_token = flask.request.args.get('hub.verify_token')
        log.info('Got verify_token: {}'.format(verify_token))

        if verify_token != WHATSAPP_VERIFY_TOKEN:
            log.info('Returning 403 to whatsapp_webook')
            return flask.abort(403)

        challenge = flask.request.args.get('hub.challenge')
        log.info('Got challenge: {}'.format(challenge))

        log.info('Returning challenge to whatsapp_webook')
        return challenge

    if flask.request.method == "POST":
        log.debug('Got call at whatsapp_webook POST!')
        log.debug('Got json: {}'.format(flask.request.json))
        # log.debug('Got headers: {}'.format(flask.request.headers))

        # {
        #   "object":"whatsapp_business_account",
        #   "entry":[
        #     {
        #       "id":"0",
        #       "changes":[
        #         {
        #           "field":"messages",
        #           "value":{
        #             "messaging_product":"whatsapp",
        #             "metadata":{
        #               "display_phone_number":"16505551111",
        #               "phone_number_id":"123456123"
        #             },
        #             "contacts":[
        #               {
        #                 "profile":{
        #                   "name":"test user name"
        #                 },
        #                 "wa_id":"16315551181"
        #               }
        #             ],
        #             "messages":[
        #               {
        #                 "from":"16315551181",
        #                 "id":"ABGGFlA5Fpa",
        #                 "timestamp":"1504902988",
        #                 "type":"text",
        #                 "text":{
        #                   "body":"this is a text message"
        #                 }
        #               }
        #             ]
        #           }
        #         }
        #       ]
        #     }
        #   ]
        # }

        request_signature = flask.request.headers.get('x-hub-signature-256')
        log.debug('Got request_signature: {}'.format(request_signature))
        if request_signature is None:
            log.error('Got missing request_signature in whatsapp_webhook POST')
            return flask.abort(403)

        app_secret = os.environ.get('APP_SECRET')
        request_signature_ok = verify_signature(flask.request.data, app_secret, request_signature)
        if not request_signature_ok:
            log.error('Got invalid request_signature in whatsapp_webhook POST')
            return flask.abort(403)

        field = flask.request.json.get('entry')[0].get('changes')[0].get('field')
        if field != 'messages':
            log.error('Got unexpected field in whatsapp_webhook POST: {}'.format(field))
            return flask.abort(403)

        message_id = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('statuses')[0].get('id')
        message_status = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('statuses')[0].get('status')  # 'sent', 'delivered', 'read'
        status_change_timestamp = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('statuses')[0].get('timestamp')
        status_change_datetime = datetime.datetime.fromtimestamp(int(status_change_timestamp))

        log.info('Got message_id: {}'.format(message_id))
        log.info('Got message_status: {}'.format(message_status))
        log.info('Got status_change_datetime: {}'.format(status_change_datetime))

        ok = db_manager.set_db_invoice_expiration_notification_message_status(message_id, message_status, status_change_datetime)
        log.info('Updated message status in db: {}'.format(ok))

        return 'ok'


def verify_signature(payload_body, secret_token, signature_header):
    # https://docs.github.com/es/webhooks/using-webhooks/validating-webhook-deliveries#python-example
    """Verify that the payload was sent from GitHub by validating SHA256.

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: App webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        log.error('Got invalid signature in verify_signature')
        return False
    log.info('Got valid signature in verify_signature')
    return True


def humanize_notifications(notifications):
    for n in notifications:
        n.status_humanized = status_to_human.get(n.status)
        n.invoice_total_humanized = to_spanish_number_str(n.invoice_total)
        n.invoice_paid_total_humanized = to_spanish_number_str(n.invoice_paid_total)
        n.invoice_unpaid_total_humanized = to_spanish_number_str(n.invoice_total - n.invoice_paid_total)
        n.client_info.account_debt_humanized = to_spanish_number_str(int(n.client_info.account_debt)) if n.client_info.account_debt else '?'
        for inv in n.invoices:
            inv.total_humanized = to_spanish_number_str(inv.total)
            inv.paid_total_humanized = to_spanish_number_str(inv.paid_total)
            inv.unpaid_humanized = to_spanish_number_str(inv.total - inv.paid_total)
            inv.invoice_datetime_humanized = inv.invoice_datetime.strftime('%d/%m/%Y')
            inv.invoice_expiration_datetime_humanized = inv.invoice_expiration_datetime.strftime('%d/%m/%Y')
    return notifications


def to_spanish_number_str(number):
    return "{:,}".format(number).replace(',', '_').replace('.', ',').replace('_', '.')


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
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.register_error_handler(404, page_not_found)
app.register_error_handler(500, internal_server_error)


db_manager = m_db_manager.DatabaseManager(db_secrets)
if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=int(os.environ.get("PORT", 8090)), ssl_context=('server.crt', 'server.key'))
