import datetime
import pymongo
import secrets as m_secrets
import string
import os
import logging
import commons
import certifi
import cryptography.fernet as fernet
import notifications as m_notifications


class DatabaseManager:
    def __init__(self, db_secrets):
        cluster_url = "cluster0.hukxd5k.mongodb.net"
        db_name = 'bss-notifications-skymedic'

        if db_secrets.get('fernet_key') is None:
            log.error('Unable to get fernet key from environment')
            exit(1)

        self.fernet = fernet.Fernet(db_secrets.get('fernet_key'))
        username = db_secrets.get('username')
        password = db_secrets.get('password')

        ca = certifi.where()
        self.client = pymongo.MongoClient('mongodb+srv://{}:{}@{}/admin?retryWrites=true&w=majority'.format(username, password, cluster_url), tlsCAFile=ca)
        self.db = self.client[db_name]
        connection_status = self.db.command({'connectionStatus': 1})
        if connection_status.get('ok'):
            user = connection_status.get('authInfo').get('authenticatedUsers')[0].get('user')
            log.debug('Opened database successfully with user {}'.format(user))
        else:
            log.error('Unable to open database')

    def add_user(self):
        name = input('Name: ')
        email = input('Email: ')
        if self.get_user(email):
            if input('User email already exists. Want to overwrite it? (y/N): ').lower() != 'y':
                return
        password = input('Password: ')
        if password == "":
            alphabet = string.ascii_letters + string.digits
            password = ''.join(m_secrets.choice(alphabet) for _ in range(16))
            log.debug('Autogenerating password: {}'.format(password))
        elif password != input('Repeat password: '):
            log.debug('Passwords are not equal')
            return

        log.debug('\n```\nName: {}\nEmail: {}\nPassword: {}\n```'.format(name, email, password))

        if input('Create user? (y/N): ').lower() != 'y':
            log.debug('User not created')
            return
        hashed_password = self.fernet.encrypt(password.encode('ascii'))
        user = {'_id': email, 'name': name, 'password': hashed_password}
        try:
            result = self.db.users.replace_one({'_id': email}, user, upsert=True)
        except Exception as e:
            log.debug('Got error when trying to add user: {}'.format(e))
            return
        if result:
            log.debug('User created successfully')
        return

    def get_user(self, username):
        try:
            db_user = self.db.users.find_one({"_id": username})
        except Exception as e:
            log.debug('Got error when trying to get user: {}'.format(e))
            return
        return db_user

    def check_user_password(self, email, password):
        user = self.get_user(email)
        if not user:
            return {'ok': False, 'reason': 'wrong_username'}
        stored_password = self.fernet.decrypt(user.get('password')).decode('ascii')
        if password != stored_password:
            return {'ok': False, 'reason': "wrong_password"}

        return {'ok': True, 'email': user.get('_id'), 'name': user.get('name')}

    def get_db_invoice_expiration_notifications(self, from_date, to_date):
        try:
            notifications = self.db.invoice_expiration_notifications.find(
                {
                    '$and': [
                        {'from_date': {'$eq': from_date}},
                        {'to_date': {'$eq': to_date}},
                    ]
                },
            )

        except Exception as e:
            log.error('Got error when trying to get invoice_expiration_notifications from {} to {} from database: {}'.format(from_date, to_date, e))
            return
        return [m_notifications.InvoiceExpirationNotification.from_db(n) for n in notifications] if notifications else []

    def set_db_invoice_expiration_notification_status(self, invoice_expiration_notification_id, status):
        # Get status first
        try:
            current_status = self.db.invoice_expiration_notifications.find_one({'_id': invoice_expiration_notification_id}, {'status': 1}).get('status')
        except Exception as e:
            log.error('Got error when trying to get invoice_expiration_notification {} from database: {}'.format(invoice_expiration_notification_id, e))
            return False

        # If status is already sent, we cannot change its status
        if current_status == 'STATUS_SENT':
            log.warning('Notification {} already sent, not updating'.format(invoice_expiration_notification_id))
            return False

        try:
            self.db.invoice_expiration_notifications.update_one({'_id': invoice_expiration_notification_id}, {'$set': {'status': status}})
        except Exception as e:
            log.error('Got error when trying to update invoice_expiration_notification {} status in database: {}'.format(invoice_expiration_notification_id, e))
            return False
        return True

    def set_db_invoice_expiration_notification_message_status(self, message_id, message_status, message_update_datetime):
        updated_at = datetime.datetime.now().astimezone(datetime.timezone.utc)
        try:
            self.db.invoice_expiration_notifications.update_one({'message_id': message_id}, {'$set': {'updated_at': updated_at,
                                                                                                      'message_status': message_status,
                                                                                                      'message_events': {message_status: message_update_datetime}}})
        except Exception as e:
            log.error('Got error when trying to update invoice_expiration_notification message {} status in database: {}'.format(message_id, e))
            return False
        return True


log = logging.getLogger()

if __name__ == '__main__':
    commons.configure_logger('db_manager')
    db_secrets = {
        'username': os.environ.get('DB_USERNAME'),
        'password': os.environ.get('DB_PASSWORD'),
        'fernet_key': os.environ.get('DB_SECRETS_KEY')
    }
    db_manager = DatabaseManager(db_secrets)
    db_manager.add_user()
