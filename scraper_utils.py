import logging
import re

default_log_format = '[%(levelname)s] [%(asctime)s] %(message)s\n'


def log_warning(msg, is_error=False):

    if 'error_log' not in logging.Logger.manager.loggerDict:
        raise NewsScrapperError("Please set up 'error_log' logger first.")

    if is_error:
        logging.getLogger('error_log').error(msg)

    else:
        logging.getLogger('error_log').warning(msg)


def setup_logger(
        name,
        level=logging.INFO,
        logfile=None,
        to_console=True,
        log_format=default_log_format):

    formatter = logging.Formatter(log_format)
    logger = logging.getLogger(name)

    logger.setLevel(level)

    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if to_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger


def extract_domain_name_from_url(link):
    base_url_pattern = re.compile('^https?://([a-zA-Z0-9.-]+)/')
    try:
        return base_url_pattern.match(link).group(1).lstrip('www.')
    except AttributeError as e:
        logging.getLogger('standard_output').warning(
            'News link [{}] does not match base_url_pattern.'.format(link)
        )


class NewsScrapperError(RuntimeError):
    """
    log error messages to logging.getLogger('error_log').
    If the logger is not set, write msg to both stdout and a file 'error.log'
    """
    logger = None

    def __init__(self, msg):
        cls = self.__class__

        # Set up logger if not yet exists
        if not cls.logger:
            cls._setup_error_logger()

        cls.logger.error(msg)

    @classmethod
    def _setup_error_logger(cls):
        if 'error_log' in logging.Logger.manager.loggerDict:
            # The logger of name 'error_log' has been setup maybe by other modules
            # Just use the already existing one
            cls.logger = logging.getLogger('error_log')
        else:
            cls.logger = setup_logger(
                'error_log', level=logging.WARNING, logfile='error.log', to_console=True
            )
