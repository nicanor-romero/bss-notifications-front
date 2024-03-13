import datetime
import logging.config
import os
import requests
import json


DEFAULT_REQUESTS_TIMEOUT_SEC = 5
DEFAULT_REQUESTS_RETRIES = 5


def configure_logger(log_file_prefix, log_level=logging.DEBUG, logs_dir='logs'):
    logs_dir_path = os.path.join(os.getcwd(), logs_dir)
    if not os.path.exists(logs_dir_path):
        os.makedirs(logs_dir_path)

    log_file_name = '{}_{:%Y%m%d_%H%M%S}.log'.format(log_file_prefix, datetime.datetime.now())
    log_file_path = os.path.join(logs_dir_path, log_file_name)

    config = get_logger_config(log_level, log_file_path)
    logging.config.dictConfig(config)
    return


def get_logger_config(log_level, log_file_path):
    return {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'json': {
                'format': '{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "message": "%(message)s", "logging.googleapis.com/labels": { "filename": "%(filename)s" } }'
            },
            'standard': {
                'format': '%(asctime)s - %(levelname)s : %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': log_level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['default'],
                'level': log_level,
                'propagate': False
            },
        }
    }


def get_config():
    config_file = os.environ.get('CONFIG_FILE', 'config/test_config.json')
    with open(config_file) as f:
        config = json.load(f)
    return config


def http_request_get(url, timeout_sec=DEFAULT_REQUESTS_TIMEOUT_SEC):
    return requests.get(url, timeout=timeout_sec)


def http_requests_get_with_retries(url, timeout_sec=DEFAULT_REQUESTS_TIMEOUT_SEC, retries=DEFAULT_REQUESTS_RETRIES):
    for i in range(retries):
        try:
            r = http_request_get(url, timeout_sec)
            return r
        except Exception as e:
            log.debug('Got error requesting URL {}: {}'.format(url, e))
            continue
    return None


log = logging.getLogger()
