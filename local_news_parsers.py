"""
Google News collects news from local news sources, such as:
  - [自由時報電子報]
    http://news.ltn.com.tw/
  - [新頭殼]
    https://newtalk.tw/
  - [中央廣播電台]
    https://news.rti.org.tw/

This module contains tools to parse these sources to grab news content.
"""
# Standard library
import json
from collections import OrderedDict
from urllib.request import urlopen
# PyPI
from bs4 import BeautifulSoup
# Local modules
import scraper_utils

parsers_registry = {}


def update_local_news_sources_list(news_entries, filename):
    """
        This function maintains a list of possible local news sources.
        Note that this is not necessary.
        This functionality is to know whether there are common local news websites
        that are not yet implemented.
    """

    local_news_sources = _read_local_news_sources_list_from_file(filename)

    for news in news_entries:
        news_hostname = scraper_utils.extract_domain_name_from_url(news.link)

        if news_hostname in local_news_sources:
            local_news_sources[news_hostname] += 1
        else:
            local_news_sources[news_hostname] = 1

    # Sort the dict "local_news_sources" by values
    local_news_sources = OrderedDict(
        sorted(local_news_sources.items(), key=lambda x: x[1], reverse=True)
    )

    with open(filename, 'w') as f:
        f.write(json.dumps(local_news_sources, indent=True))


def _register_local_source(name, cls):
    global parsers_registry
    parsers_registry[name] = cls


def _read_local_news_sources_list_from_file(filename):
    try:
        with open(filename, 'r') as f:
            return json.loads(f.read())
    except FileNotFoundError as e:
        # Create an empty file
        open(filename, 'a').close()
        return {}
    except json.decoder.JSONDecodeError as e:
        msg = "Fail to parse the content of file '%s' as JSON. " % filename
        scraper_utils.log_warning(msg)
        return {}


class LocalNewsMeta(type):
    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)

        if bases != (object,):
            # Skip the (abstract) base class (HtmlNewsParser)
            for domain_name in cls.source_base_urls:
                _register_local_source(domain_name, cls)

        return cls


class HtmlNewsParser(object, metaclass=LocalNewsMeta):
    """
    Should NOT be instanciated directly.
    """
    source_base_urls = []

    def get_news_content(
        self, url, ancestor_tag=None, dict_ancestor_attr=None, raise_error=False
    ):

        if not ancestor_tag:
            return self._get_news_content_by_default(url)

        try:
            news_content = self._get_news_content_by_p_tags(
                url, ancestor_tag, dict_ancestor_attr
            )
        except AttributeError:
            if raise_error:
                raise  # So that the caller can handle the AttributeError

            msg = (
                "Try to get news content by <p> tags inside <%s> from [%s], but fail. "
                "Maybe the html content of the local news source has been changed."
                % (ancestor_tag, url)
            )
            scraper_utils.log_warning(msg)
            news_content = self._get_news_content_by_default(url)

        return news_content

    def _get_news_content_by_default(self, url):
        try:
            news_content = self._get_news_content_by_meta_name(url, "description")
        except (TypeError, KeyError) as e:
            try:
                news_content = self._get_news_content_by_meta_name(url, "Description")
            except (TypeError, KeyError) as e:
                msg = (
                    "Try to get news content by meta description from [%s], but fail."
                    % url
                )
                scraper_utils.log_warning(msg)

                # news_content = self._get_beautifulsoup_obj(url).get_text()
                news_content = "<Fail to get news_content>"

        return news_content

    def _get_news_content_by_p_tags(self, url, ancestor_tag, dict_ancestor_attr):

        bsobj = self._get_beautifulsoup_obj(url)

        paragraphs = bsobj.find(ancestor_tag, dict_ancestor_attr).findAll('p')

        return ''.join(p.get_text() for p in paragraphs)

    def _get_news_content_by_meta_name(self, url, meta_name):
        bsobj = self._get_beautifulsoup_obj(url)

        description_in_meta = bsobj.find("meta", {"name": meta_name})["content"]

        if description_in_meta and isinstance(description_in_meta, str):
            return description_in_meta

        else:
            msg = (
                "Get empty or non-string news content by meta '%s' from [%s]. "
                "Currently null string is returned as a workaround."
                % url
            )
            scraper_utils.log_warning(msg)

            return ""

    def _get_beautifulsoup_obj(self, url):

        # check whether the URL belong to this local news source
        self._check_url(url)

        # May raise HTTPError, URLError
        # Should be handled by caller
        html = urlopen(url)
        bsobj = BeautifulSoup(html, "html.parser")
        return bsobj

    def _check_url(self, url):

        target_base_url = scraper_utils.extract_domain_name_from_url(url)

        # source is generally shorter or equal to target_base_url
        valid = any(source in target_base_url for source in self.__class__.source_base_urls)

        if not valid:
            raise scraper_utils.NewsScrapperError(
                "URL [%s] does not match any of base_urls: %s"
                % (url, self.__class__.source_base_urls)
            )


class DefaultHtmlNewsParser(HtmlNewsParser):

    def _check_url(self, url):
        pass


class LtnHtmlNewsParser(HtmlNewsParser):

    source_base_urls = ['ltn.com.tw']

    def get_news_content(self, url):
        """Ltn has two common html formats...
        """

        possible_class_names = ["text", "news_content", "boxTitle", "conbox", "content"]

        for class_name in possible_class_names[:-1]:
            try:
                return super().get_news_content(
                    url, "div", {"class": class_name}, raise_error=True
                )
            except AttributeError:
                continue

        # The last one
        return super().get_news_content(
            url, "div", {"class": possible_class_names[-1]}  # No 'raise_error=True' here
        )


class CnaHtmlNewsParser(HtmlNewsParser):

    source_base_urls = ['cna.com.tw']

    def get_news_content(self, url):
        return super().get_news_content(url, "div", {"class": "article_box"})


class UdnHtmlNewsParser(HtmlNewsParser):

    source_base_urls = ['udn.com']

    def get_news_content(self, url):
        return super().get_news_content(url, "div", {"id": "story_body_content"})


class EtodayHtmlNewsParser(HtmlNewsParser):

    source_base_urls = ['ettoday.net']

    def get_news_content(self, url):
        return super().get_news_content(url, "div", {"class": "story"})


if __name__ == '__main__':  # For test

    print(parsers_registry)

    print('##########################')

    scraper_utils.setup_logger('error_log', to_console=True)
    parser = LtnHtmlNewsParser()
    content = parser.get_news_content('http://news.ltn.com.tw/news/society/breakingnews/2346006')
    print(content)
    print()
    content = parser.get_news_content('http://ent.ltn.com.tw/news/breakingnews/2345256')
    print(content)
    print()

    parser = CnaHtmlNewsParser()
    content = parser.get_news_content('http://www.cna.com.tw/news/afe/201802210255-1.aspx')
    print(content)
    print()

    parser = UdnHtmlNewsParser()
    content = parser.get_news_content('https://udn.com/news/story/6811/2992548')
    print(content)
    print()

    parser = EtodayHtmlNewsParser()
    content = parser.get_news_content('https://www.ettoday.net/news/20180221/1117010.htm')
    print(content)
    print()
