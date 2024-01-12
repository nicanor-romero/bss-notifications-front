
class InvoiceExpirationNotification:
    STATUS_PENDING_APPROVAL = 'STATUS_PENDING_APPROVAL'
    STATUS_PENDING_DISPATCH = 'STATUS_PENDING_DISPATCH'
    STATUS_SENT = 'STATUS_SENT'
    STATUS_DISABLED = 'STATUS_DISABLED'
    STATUS_EXPIRED = 'STATUS_EXPIRED'

    def __init__(self, client_info, account_executive, invoice_total, invoice_paid_total, invoices, from_date, to_date):
        self.id = '{}:{}:{}'.format(client_info.id, from_date.strftime('%Y%m%d'), to_date.strftime('%Y%m%d'))
        self.client_info = client_info
        self.account_executive = account_executive
        self.invoice_total = invoice_total
        self.invoice_paid_total = invoice_paid_total
        self.from_date = from_date
        self.to_date = to_date
        self.invoices = invoices
        self.status = InvoiceExpirationNotification.STATUS_PENDING_APPROVAL
        return

    def __repr__(self):
        return '{} ({} - {}): ${}/${}'.format(self.client_info.name, self.from_date.strftime('%Y/%m/%d'), self.to_date.strftime('%Y/%m/%d'), self.invoice_paid_total, self.invoice_total)

    @staticmethod
    def from_db(db_obj):
        client_info = ClientInfo.from_db(db_obj.get('client_info'))
        account_executive = AccountExecutive.from_db(db_obj.get('account_executive'))
        invoices = [SaleInvoice.from_db(inv) for inv in db_obj.get('invoices')]
        obj = InvoiceExpirationNotification(
            client_info,
            account_executive,
            db_obj.get('invoice_total'),
            db_obj.get('invoice_paid_total'),
            invoices,
            db_obj.get('from_date'),
            db_obj.get('to_date')
        )
        return obj

    def to_db(self):
        db_obj = self.__dict__.copy()
        db_obj['client_info'] = self.client_info.to_db()
        db_obj['account_executive'] = self.account_executive.to_db()
        db_obj['invoices'] = [inv.to_db() for inv in self.invoices]
        return db_obj


class ClientInfo:
    def __init__(self, client_id, name, tin, phone, mobile_phone, email, account_manager, company):
        self.id = client_id
        self.name = name
        self.tin = tin
        self.phone = None if phone is None or phone == "" else phone
        self.mobile_phone = None if mobile_phone is None or mobile_phone == "" else mobile_phone
        self.email = None if email is None or email == "" else email
        self.account_manager = account_manager
        self.company = company
        return

    @staticmethod
    def from_db(db_obj):
        obj = ClientInfo(
            db_obj.get('id'),
            db_obj.get('name'),
            db_obj.get('tin'),
            db_obj.get('phone'),
            db_obj.get('mobile_phone'),
            db_obj.get('email'),
            db_obj.get('account_manager'),
            db_obj.get('company')
        )
        return obj

    def to_db(self):
        db_obj = self.__dict__.copy()
        return db_obj


class AccountExecutive:
    def __init__(self, user_id, user_name, phone, email):
        self.user_id = user_id
        self.user_name = user_name
        self.phone = phone
        self.email = email
        return

    @staticmethod
    def from_db(db_obj):
        obj = AccountExecutive(
            db_obj.get('user_id'),
            db_obj.get('user_name'),
            db_obj.get('phone'),
            db_obj.get('email')
        )
        return obj

    def to_db(self):
        db_obj = self.__dict__.copy()
        return db_obj


class SaleInvoice:
    def __init__(self, invoice_number, total, paid_total, invoice_datetime, invoice_expiration_datetime):
        self.invoice_number = invoice_number
        self.total = total
        self.paid_total = paid_total
        self.invoice_datetime = invoice_datetime
        self.invoice_expiration_datetime = invoice_expiration_datetime
        return

    @staticmethod
    def from_db(db_obj):
        obj = SaleInvoice(
            db_obj.get('invoice_number'),
            db_obj.get('total'),
            db_obj.get('paid_total'),
            db_obj.get('invoice_datetime'),
            db_obj.get('invoice_expiration_datetime'),
        )
        return obj

    def to_db(self):
        db_obj = self.__dict__.copy()
        return db_obj
