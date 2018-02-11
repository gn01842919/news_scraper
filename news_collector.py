from news_sources import news_source_registry
from urllib.error import HTTPError, URLError


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
    retrieve_registered_news_by_rss()
