"""
Google news collects news from local sources.
So... Need to parse these sources to grab news content.
"""
# Standard library
from urllib.request import urlopen
# PyPI
from bs4 import BeautifulSoup
from news_collector import extract_news_source_from_url


def _register_local_source(self, url):
    pass


class HtmlNewsParser(object):

    def __init__(self):
        self.source_base_urls = []

    def get_news_content(self, url, ancestor_tag=None, dict_ancestor_attr=None):

        if not ancestor_tag:
            return self._get_news_content_by_default(url)

        try:
            news_content = self._get_news_content_by_p_tags(
                url, ancestor_tag, dict_ancestor_attr
            )
        except AttributeError:
            ########
            # 這是最後一招，寫個警告訊息!!!!
            ########
            news_content = self._get_news_content_by_default(url)

        return news_content

    def _get_news_content_by_default(self, url):
        try:
            news_content = self._get_news_content_by_meta_name(url, "description")
        except TypeError as e:
            try:
                news_content = self._get_news_content_by_meta_name(url, "Description")
            except TypeError as e:
                ########
                # 這是最後一招，寫個警告訊息!!!!
                ########
                news_content = self._get_beautifulsoup_obj(url).get_text()

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
            # Should use logging to capture
            raise RuntimeError(
                "No description is found for [%s]. Found: [%s]" % (url, description_in_meta)
            )

    def _get_beautifulsoup_obj(self, url):

        # check whether the URL belong to this local news source
        if not self._check_url(url):
            raise RuntimeError(
                "URL [%s] does not match any of base_urls: %s" % (url, self.source_base_urls)
            )

        # May raise HTTPError, URLError
        # Should be handled by caller
        html = urlopen(url)
        bsobj = BeautifulSoup(html, "html.parser")
        return bsobj

    def _check_url(self, url):
        target_base_url = extract_news_source_from_url(url)
        # source is generally shorter or equal to target_base_url
        return any(source in target_base_url for source in self.source_base_urls)


class LtnHtmlNewsParser(HtmlNewsParser):

    def __init__(self):
        self.source_base_urls = ['ltn.com.tw']

    def get_news_content(self, url):
        return super().get_news_content(url, "div", {"class": "news_content"})


class CnaHtmlNewsParser(HtmlNewsParser):

    def __init__(self):
        self.source_base_urls = ['cna.com.tw']

    def get_news_content(self, url):
        return super().get_news_content(url, "div", {"class": "article_box"})


class UdnHtmlNewsParser(HtmlNewsParser):

    def __init__(self):
        self.source_base_urls = ['udn.com']

    def get_news_content(self, url):
        return super().get_news_content(url, "div", {"id": "story_body_content"})


class EtodayHtmlNewsParser(HtmlNewsParser):

    def __init__(self):
        self.source_base_urls = ['ettoday.net']

    def get_news_content(self, url):

        return super().get_news_content(url, "div", {"class": "story"})


if __name__ == '__main__':
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
