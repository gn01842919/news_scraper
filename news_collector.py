from news_sources import news_source_registry
from urllib.error import HTTPError, URLError


def retrieve_registered_news_by_rss():
    for class_name, NewsSourceClass in news_source_registry.items():
        news_src = NewsSourceClass()
        print('-' * 10)
        print(class_name)
        print('-' * 10)

        for category in news_src.categories:
            try:
                feed_obj = news_src.get_feed_object(category)
            except (HTTPError, URLError):
                # The rss link is invalid or has problems
                # To-Do: Maybe the url should be logged.
                continue

            print(feed_obj)
            for entry in feed_obj.entries:
                print(entry.title)


if __name__ == '__main__':
    print(news_source_registry)
    retrieve_registered_news_by_rss()
