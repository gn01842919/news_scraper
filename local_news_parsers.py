"""This module contains tools to parse a news link to extract news content.

Purpose:
    Google RSS News collects news from local news sources, such as:
      - [自由時報電子報]
        http://news.ltn.com.tw/
      - [新頭殼]
        https://newtalk.tw/
      - [中央廣播電台]
        https://news.rti.org.tw/

    But it does not contain the news content in the RSS feed itself.
    The purpose of this module is to grab the news content from
    the actual news source.

Attributes:
    _PARSER_REGISTRY (dict): Maps domain names to local news parsers.
        <Key>: The domain name of the local news source.
        <Value>: The local news parser class.

        When writing a class that inherits the base class ``HtmlNewsParser``,
        it is registered in ``_PARSER_REGISTRY`` automatically.

"""
# Standard library
import json
from collections import OrderedDict
from urllib.request import urlopen
# PyPI
from bs4 import BeautifulSoup
# Local modules
import scraper_utils

_PARSER_REGISTRY = {}


def update_local_news_sources_list(news_entries, filename):
    """This function maintains a list of possible local news sources to a file.

    Note that this is not necessarily.
    This purpose is to know whether there are common local news websites
    whose parsers are not yet implemented.

    Args:
        news_entries (Iterable(scraper_models.NewsRSSEntry)): News eitries
            to extract the news source websites from.

        filename (str): The name of the file to store the updated list
            and to read the current list from.

    """

    local_news_sources = scraper_utils.read_json_from_file(filename)

    for news in news_entries:
        news_hostname = scraper_utils.extract_domain_name_from_url(news.link)

        if news_hostname in local_news_sources:
            local_news_sources[news_hostname] += 1
        else:
            local_news_sources[news_hostname] = 1

    # Sort the dict "local_news_sources" by values
    sorted_local_news_sources = OrderedDict(
        sorted(local_news_sources.items(), key=lambda x: x[1], reverse=True)
    )

    with open(filename, 'w') as outfile:
        outfile.write(json.dumps(sorted_local_news_sources, indent=True))


def get_local_parser_registry():
    """Get the dict mapping domain names to local news parsers.

    Returns:
        dict: ``_PARSER_REGISTRY``

    """
    return _PARSER_REGISTRY


def _register_local_source(name, cls):
    _PARSER_REGISTRY[name] = cls


def _get_local_news_sources(filename):
    """Read local news source list from file.

    Returns:
        dict: A JSON config.
    """
    try:
        with open(filename, 'r') as infile:
            return json.loads(infile.read())
    except FileNotFoundError:
        # Create an empty file
        open(filename, 'a').close()
        return {}
    except json.decoder.JSONDecodeError:
        msg = "Fail to parse the content of file '%s' as JSON. " % filename
        scraper_utils.log_warning(msg)
        return {}


class LocalNewsMeta(type):
    """Meta class for ``HtmlNewsParser`` to register subclasses.

    To register <domain_name, parser_class> mappings to ``_PARSER_REGISTRY``.

    Note that the base class itself will not be registered.

    """
    def __new__(mcs, name, bases, class_dict):
        cls = type.__new__(mcs, name, bases, class_dict)

        # Skip the (abstract) base class (HtmlNewsParser)
        if bases != (object,):
            for domain_name in cls.source_base_urls:
                _register_local_source(domain_name, cls)

        return cls


class HtmlNewsParser(object, metaclass=LocalNewsMeta):
    """Base class for local news parsers.

    Subclasses of this class are registered to ``_PARSER_REGISTRY``.
    Note that this class can not be instanciated.

    Attributes:
        source_base_urls (list(str)): Domain names for the local news source.

    """
    source_base_urls = []

    def get_news_content_from_url(self, url):
        """Get news content from the local news source.

        Args:
            url (str): The link of the local news.

        Returns:
            str: News content of the local news.

        """
        return self._get_news_content(url)

    def _get_news_content(self, url, ancestor_tag=None,
                          dict_ancestor_attr=None, raise_error=False):
        """Get news content from url.

        Args:
            url (str): The link of the local news.

            ancestor_tag (str): The html tag in which the news content lies.

            dict_ancestor_attr (dict, optional): Attributes of the target
                 ``ancestor_tag``. Defaults to None.

            raise_error (bool, optional): Whether to raise AttributeError
                when fail to find the target ``ancestor_tag``.

        Returns:
            str: News content of the local news.

        Raises:
            AttributeError: If fail to find the target ``ancestor_tag`` and
                ``raise_error`` is set to True.

        Example:
            news_content = get_news_content(
                    url, "div", {"class": "article"}, raise_error=True
                )

            This will try to find the tag ``<div class="article">``, and
            retrieve the news content inside the tag.

            If not ``ancestor_tag`` is assigned, this method will try to
            find ``<meta name="description" content="......">`` and retrieve
            the news content from it.

        """

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
        except (TypeError, KeyError):
            try:
                news_content = self._get_news_content_by_meta_name(url, "Description")
            except (TypeError, KeyError):
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
    """Parser for local news sources whose html_parser is not yet implemented.
    """

    def _check_url(self, url):
        pass


class LtnHtmlNewsParser(HtmlNewsParser):
    """Parser for the local news source "自由時報 (LTN)".

    Attribute:
        source_base_urls (list(str)): Posible domain names for this local news source.

    """

    source_base_urls = ['ltn.com.tw']

    def get_news_content_from_url(self, url):
        """Get news content from the news link.

        Args:
            url (str): The link of the local news.

        Returns:
            str: News content of the local news.

        """
        # Ltn has many common html formats...
        possible_class_names = ["text", "news_content", "boxTitle", "conbox", "content"]

        for class_name in possible_class_names[:-1]:
            try:
                return self._get_news_content(
                    url, "div", {"class": class_name}, raise_error=True
                )
            except AttributeError:
                continue

        # The last one should not have to raise Attrubute errors, so handle it seperately.
        return self._get_news_content(
            url, "div", {"class": possible_class_names[-1]}  # No 'raise_error=True' here
        )


class CnaHtmlNewsParser(HtmlNewsParser):
    """Parser for the local news source "中央通訊社 (CNA)".

    Attribute:
        source_base_urls (list(str)): Posible domain names for this local news source.

    """
    source_base_urls = ['cna.com.tw']

    def get_news_content_from_url(self, url):
        """Get news content from the news link.

        Args:
            url (str): The link of the local news.

        Returns:
            str: News content of the local news.

        """
        return self._get_news_content(url, "div", {"class": "article_box"})


class UdnHtmlNewsParser(HtmlNewsParser):
    """Parser for the local news source "聯合新聞網 (UDN)".

    Attribute:
        source_base_urls (list(str)): Posible domain names for this local news source.

    """
    source_base_urls = ['udn.com']

    def get_news_content_from_url(self, url):
        """Get news content from the news link.

        Args:
            url (str): The link of the local news.

        Returns:
            str: News content of the local news.

        """
        return self._get_news_content(url, "div", {"id": "story_body_content"})


class EtodayHtmlNewsParser(HtmlNewsParser):
    """Parser for the local news source "ETtoday 新聞雲".

    Attribute:
        source_base_urls (list(str)): Posible domain names for this local news source.

    """
    source_base_urls = ['ettoday.net']

    def get_news_content_from_url(self, url):
        """Get news content from the news link.

        Args:
            url (str): The link of the local news.

        Returns:
            str: News content of the local news.

        """
        return self._get_news_content(url, "div", {"class": "story"})
