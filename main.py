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
STATUS_SEND_CONFIRMED = 'STATUS_SEND_CONFIRMED'
STATUS_RECEIVED = 'STATUS_RECEIVED'
STATUS_READ = 'STATUS_READ'
STATUS_DISABLED = 'STATUS_DISABLED'
STATUS_EXPIRED = 'STATUS_EXPIRED'
STATUS_DISPATCH_ERROR = 'STATUS_DISPATCH_ERROR'

AREA_CODES = ['11', '220', '2202', '221', '2221', '2223', '2224', '2225', '2226', '2227', '2229', '223', '2241', '2242', '2243', '2244', '2245', '2246', '2252', '2254', '2255', '2257', '2261', '2262', '2264', '2265', '2266', '2267', '2268', '2271', '2272', '2273', '2274', '2281', '2283', '2284', '2285', '2286', '2291', '2292', '2296', '2297', '230', '2302', '2314', '2316', '2317', '2320', '2323', '2324', '2325', '2326', '2331', '2333', '2334', '2335', '2336', '2337', '2338', '2342', '2343', '2344', '2345', '2346', '2352', '2353', '2354', '2355', '2356', '2357', '2358', '236', '237', '2392', '2393', '2394', '2395', '2396', '2473', '2474', '2475', '2477', '2478', '249', '260', '261', '2622', '2624', '2625', '2626', '263', '264', '2646', '2647', '2648', '2651', '2655', '2656', '2657', '2658', '266', '280', '2901', '2902', '2903', '291', '2920', '2921', '2922', '2923', '2924', '2925', '2926', '2927', '2928', '2929', '2931', '2932', '2933', '2934', '2935', '2936', '294', '2940', '2942', '2945', '2946', '2948', '2952', '2953', '2954', '2962', '2963', '2964', '2966', '297', '2972', '298', '2982', '2983', '299', '3327', '3329', '336', '3382', '3385', '3387', '3388', '3400', '3401', '3402', '3404', '3405', '3406', '3407', '3408', '3409', '341', '342', '343', '3435', '3436', '3437', '3438', '3442', '3444', '3445', '3446', '3447', '345', '3454', '3455', '3456', '3458', '3460', '3462', '3463', '3464', '3465', '3466', '3467', '3468', '3469', '3471', '3472', '3476', '348', '3482', '3483', '3487', '3489', '3491', '3492', '3493', '3496', '3497', '3498', '351', '3521', '3522', '3524', '3525', '353', '3532', '3533', '3537', '3541', '3542', '3543', '3544', '3546', '3547', '3548', '3549', '3562', '3563', '3564', '3571', '3572', '3573', '3574', '3575', '3576', '358', '3582', '3583', '3584', '3585', '362', '364', '370', '3711', '3715', '3716', '3718', '3721', '3725', '3731', '3734', '3735', '3741', '3743', '3751', '3754', '3755', '3756', '3757', '3758', '376', '3772', '3773', '3774', '3775', '3777', '3781', '3782', '3786', '379', '380', '381', '3821', '3825', '3826', '3827', '383', '3832', '3835', '3837', '3838', '3841', '3843', '3844', '3845', '3846', '385', '3854', '3855', '3856', '3857', '3858', '3861', '3862', '3863', '3865', '3867', '3868', '3869', '387', '3873', '3876', '3877', '3878', '388', '3885', '3886', '3887', '3888', '3891', '3892', '3894']

status_to_human = {
    STATUS_PENDING_APPROVAL: 'Pendiente',
    STATUS_PENDING_DISPATCH: 'Enviando...',
    STATUS_SENT: 'Enviada',
    STATUS_SEND_CONFIRMED: 'Envío confirmado',
    STATUS_RECEIVED: 'Recibido',
    STATUS_READ: 'Leído',
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
    expire_in = datetime.timedelta(days=10)
    if flask.request.args and flask.request.args.get('expire_in'):
        expire_in_days = flask.request.args.get('expire_in')
        expire_in = datetime.timedelta(days=int(expire_in_days))

    invoice_expiration_day = datetime.datetime.combine(datetime.datetime.today() + expire_in, datetime.datetime.min.time())

    # Get invoices created 30 days before the desired expiration day
    from_date = invoice_expiration_day - datetime.timedelta(days=30)
    to_date = from_date

    log.info('Getting invoice expiration notifications from {} to {}'.format(from_date, to_date))

    notifications = db_manager.get_db_invoice_expiration_notifications(from_date, to_date)
    notifications = humanize_notifications(notifications)
    # Sort notifications by client name
    notifications = sorted(notifications, key=lambda n: n.client_info.name)
    return flask.render_template('home.html', notifications=notifications, expire_in=expire_in.days, **global_variables())


def humanize_notifications(notifications):
    for n in notifications:
        n.status_humanized = status_to_human.get(n.status)
        n.invoice_total_humanized = to_spanish_number_str(n.invoice_total)
        n.invoice_paid_total_humanized = to_spanish_number_str(n.invoice_paid_total)
        n.invoice_unpaid_total_humanized = to_spanish_number_str(n.invoice_total - n.invoice_paid_total)
        n.client_info.phone_valid = check_if_phone_is_valid(n.client_info.phone)
        n.client_info.phone_humanized = humanize_phone_number(n.client_info.phone) if n.client_info.phone_valid else n.client_info.phone
        n.client_info.account_debt_humanized = to_spanish_number_str(int(n.client_info.account_debt)) if n.client_info.account_debt else '?'
        for inv in n.invoices:
            inv.total_humanized = to_spanish_number_str(inv.total)
            inv.paid_total_humanized = to_spanish_number_str(inv.paid_total)
            inv.unpaid_humanized = to_spanish_number_str(inv.total - inv.paid_total)
            inv.invoice_datetime_humanized = inv.invoice_datetime.strftime('%d/%m/%Y')
            inv.invoice_expiration_datetime_humanized = inv.invoice_expiration_datetime.strftime('%d/%m/%Y')
        n.created_at_humanized = n.created_at.strftime('%d/%m/%Y %H:%M:%S')
        n.updated_at_humanized = n.updated_at.strftime('%d/%m/%Y %H:%M:%S')
    return notifications


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


@app.route('/history', methods=["GET"])
@check_if_logged_in
def history():
    if flask.request.args is None:
        return flask.render_template('history.html', **global_variables())

    # Get query params
    start_date_str = flask.request.args.get('start_date')
    end_date_str = flask.request.args.get('end_date')
    # Mandatory query params
    if start_date_str is None or end_date_str is None:
        return flask.render_template('history.html', **global_variables())

    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')

    client_id = flask.request.args.get('client_id') if flask.request.args.get('client_id') != '' else None
    client_name = flask.request.args.get('client_name') if flask.request.args.get('client_name') != '' else None

    # Get notifications from db
    notifications = db_manager.get_db_invoice_expiration_client_notifications(client_id, client_name, start_date, end_date)
    notifications = humanize_notifications(notifications)
    notifications = sorted(notifications, key=lambda n: n.updated_at)
    return flask.render_template('history.html', notifications=notifications, **global_variables())



@app.route('/whatsapp-webhook', methods=["GET", "POST"])
def whatsapp_webhook():
    if flask.request.method == "GET":
        # [('hub.mode', 'subscribe'), ('hub.challenge', '1776433461'), ('hub.verify_token', '8v34L0HH3sq0iu1fnqx2JUPJ')])
        log.debug('Got call at whatsapp_webook GET!')

        whatsapp_verify_token = db_manager.get_whatsapp_verify_token_secret(config.get('general').get('tenant_id')).get('verify_token')

        verify_token = flask.request.args.get('hub.verify_token')
        log.info('Got verify_token: {}'.format(verify_token))

        if verify_token != whatsapp_verify_token:
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

        app_secret = db_manager.get_whatsapp_app_secret(config.get('whatsapp').get('app_id')).get('app_secret')
        request_signature_ok = verify_signature(flask.request.data, app_secret, request_signature)
        if not request_signature_ok:
            log.error('Got invalid request_signature in whatsapp_webhook POST')
            return flask.abort(403)

        field = flask.request.json.get('entry')[0].get('changes')[0].get('field')
        if field != 'messages':
            log.error('Got unexpected field in whatsapp_webhook POST: {}'.format(field))
            return flask.abort(403)

        if flask.request.json.get('entry')[0].get('changes')[0].get('value').get('statuses'):
            log.info('Got status change in whatsapp_webhook POST')

            message_id = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('statuses')[0].get('id')
            message_status = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('statuses')[0].get('status')  # 'sent', 'delivered', 'read'
            status_change_timestamp = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('statuses')[0].get('timestamp')
            status_change_datetime = datetime.datetime.fromtimestamp(int(status_change_timestamp))

            log.info('Got message_id: {}'.format(message_id))
            log.info('Got message_status: {}'.format(message_status))
            log.info('Got status_change_datetime: {}'.format(status_change_datetime))

            if message_status == 'sent':
                notification_status = STATUS_SEND_CONFIRMED
            elif message_status == 'delivered':
                notification_status = STATUS_RECEIVED
            elif message_status == 'read':
                notification_status = STATUS_READ
            else:
                log.error('Got unexpected message_status in whatsapp_webhook POST: {}'.format(message_status))
                return 'ok'

            ok = db_manager.set_db_invoice_expiration_notification_message_status(message_id, notification_status, message_status, status_change_datetime)
            log.info('Updated message status in db: {}'.format(ok))

        elif flask.request.json.get('entry')[0].get('changes')[0].get('value').get('messages'):
            log.info('Got new message in whatsapp_webhook POST')

            try:
                message_timestamp = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('messages')[0].get('timestamp')
                message_origin = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('messages')[0].get('from')
                message_content = flask.request.json.get('entry')[0].get('changes')[0].get('value').get('messages')[0].get('text').get('body')
                log.info('Got message from {} at {}: {}'.format(message_origin, message_timestamp, message_content))

            except Exception as e:
                log.error('Got error while trying to get message content: {}'.format(e))
                return 'ok'

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


def to_spanish_number_str(number):
    return "{:,}".format(number).replace(',', '_').replace('.', ',').replace('_', '.')


def check_if_phone_is_valid(phone):
    # In Argentina, area codes are two, three, or four digits long (after the initial zero).
    # Local customer numbers are six to eight digits long.
    # https://en.wikipedia.org/wiki/Telephone_numbers_in_Argentina

    # En la Argentina, los números de teléfono tienen un total de diez dígitos,
    # compuesto por el código de área (indicador interurbano) y el número de abonado, sin considerar el prefijo telefónico internacional.
    # https://www.argentina.gob.ar/pais/codigo-telefonia

    # Remove leading zero
    if phone[0] == '0':
        phone = phone[1:]

    # Remove leading 15
    if phone[:2] == '15':
        phone = phone[2:]

    if phone is None or phone == "" or len(phone) != 10:
        return False
    return True


def humanize_phone_number(phone):
    # Remove leading zero
    if phone[0] == '0':
        phone = phone[1:]

    # Remove leading 15
    if phone[:2] == '15':
        phone = phone[2:]

    if phone[:4] in AREA_CODES:
        return '({}) {}'.format(phone[:4], phone[4:])
    elif phone[:3] in AREA_CODES:
        return '({}) {}'.format(phone[:3], phone[3:])
    elif phone[:2] in AREA_CODES:
        return '({}) {}'.format(phone[:2], phone[2:])
    else:
        return phone



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


commons.configure_logger('bss_notifications_front')
log = logging.getLogger()
config = commons.get_config()
db_secrets = {
    'username': os.environ.get('DB_USERNAME'),
    'password': os.environ.get('DB_PASSWORD'),
    'fernet_key': os.environ.get('DB_SECRETS_KEY')
}
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.register_error_handler(404, page_not_found)
app.register_error_handler(500, internal_server_error)


db_manager = m_db_manager.DatabaseManager(config.get('db'), db_secrets)
if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=int(os.environ.get("PORT", 8090)), ssl_context=('server.crt', 'server.key'))
