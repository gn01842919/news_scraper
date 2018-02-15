from news_sources import news_source_registry
from urllib.error import HTTPError, URLError
import logging
import os

default_log_format = '[%(levelname)s] (%(asctime)s) %(message)s'


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


def retrieve_registered_news_by_rss():

    # Reset the output file
    with open("output.txt", "w") as f:
        f.write('')

    for class_name, NewsSourceClass in news_source_registry.items():
        news_src = NewsSourceClass()

        for category in news_src.categories:
            try:
                feed_obj = news_src.get_feed_object(category)
            except (HTTPError, URLError):
                # The rss link is invalid or has problems
                # To-Do: Maybe the url should be logged.
                continue

            with open("output.txt", "a") as f:
                print(feed_obj, file=f)
                for entry in feed_obj.entries:
                    info = (
                        "     --------------------\n"
                        "     [Title]: {}\n"
                        "     [Link] : {}\n"
                        "     [Desc] : {}\n"
                        "     [Time] : {}\n"
                        "     --------------------\n"
                        .format(
                            entry.title, entry.link, entry.description, entry.published_time
                        )
                    )
                    print(info, file=f)


if __name__ == '__main__':

    # set logger for HTTP and URL errors
    http_error_log_path = os.path.join(os.getcwd(), 'RSS_URL_Problems.log')
    setup_logger('invalid_rss_urls', logfile=http_error_log_path, to_console=True)

    setup_logger('standard_output', to_console=True, level=logging.DEBUG)

    retrieve_registered_news_by_rss()
