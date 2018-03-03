"""
"""
import scraper_utils


class RssFeed(object):
    def __init__(self, title, subtitle, link, language, published_time, entries):
        self.title = title
        self.subtitle = subtitle
        self.link = link
        self.language = language
        self.published_time = published_time
        self.entries = entries  # A tuple of NewsRSSEntry

    def __repr__(self):
        return (
            "======== <RssFeed object at {0}> ========\n"
            "[Title]       : {feed_obj.title}\n"
            "[Subtitle]    : {feed_obj.subtitle}\n"
            "[Link]        : {feed_obj.link}\n"
            "[Language]    : {feed_obj.language}\n"
            "[Published]   : {feed_obj.published_time}\n"
            "[# of Entries]: {1}\n"
            "===============================================\n"
            .format(
                hex(id(self)),
                len(self.entries),
                feed_obj=self
            )
        )


class NewsRSSEntry(object):
    def __init__(
        self, title, description, link, published_time, source,
        category=None, tags=None, rules=None
    ):
        self.title = title
        self.description = description
        self.link = link
        self.published_time = published_time
        self.source = source
        self.rule_score_map = {}  # rule ==> score, will be set in news_collector.py
        self.tags = tags.copy() if tags else set()  # .copy() -> shallow copy

        if rules:
            self.set_rules(rules)

        # Category defined by RSS feed link
        if category:
            self.tags.add(category)

    def set_rules(self, rules):
        for rule in rules:
            score = self._compute_score_by_rule(rule)
            self.rule_score_map[rule] = score
            self._set_tags_from_rule(rule, score)

    @property
    def total_score(self):
        if not self.rule_score_map:
            scraper_utils.log_warning('No scraping rule set for %s' % str(self))

        return sum(score for score in self.rule_score_map.values() if score > 0)

    def _set_tags_from_rule(self, rule, score):
        if score > 0:
            self.tags.update(rule.tags)  # shallow copy

    def _compute_score_by_rule(self, rule):
        """
        Score:
            < 0 ==> excluded     (by rule.excluded_keywords)
            > 0 ==> of interest  (by rule.included_keywords)
            = 0 ==> others (not of interest) (does not contains "all" included_keywords)
        """
        score = 0

        for keyword in rule.excluded_keywords:
            if keyword in self.title:
                score -= 10

        if score < 0:
            # Excluded. No more evaluation.
            return score

        contains_all_keywords = True
        for keyword in rule.included_keywords:
            # Should change to analyse the content of the news

            keyword_occurrences_in_title = self.title.count(keyword)
            if keyword_occurrences_in_title > 0:
                score += keyword_occurrences_in_title * 10

            keyword_occurrences_in_description = self.description.count(keyword)
            if keyword_occurrences_in_description > 0:
                score += keyword_occurrences_in_description * 1

            if not keyword_occurrences_in_title and not keyword_occurrences_in_description:
                # If any of the keywords does not appear, this news does not pass the rule
                contains_all_keywords = False

        if not contains_all_keywords:
            score = 0

        return score

    def __repr__(self):
        return (
            "  #-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#\n"
            "  -- <NewsRSSEntry object at {0}> --\n"
            "  [Title]       : {news_obj.title}\n"
            "  [Description] : {news_obj.description}\n"
            "  [Link]        : {news_obj.link}\n"
            "  [Published]   : {news_obj.published_time}\n"
            "  [Source]      : {news_obj.source}\n"
            "  [Tags]        : {news_obj.tags}\n"
            "  [Rules]       : {rules}\n"
            "  #-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#\n"
            .format(
                hex(id(self)),
                news_obj=self,
                rules={str(rule): score for rule, score in self.rule_score_map.items()}
            )
        )

    def __str__(self):
        return "<NewsRSSEntry '%s'>" % self.title


class ScrapingRule(object):
    def __init__(self, name, inc_kw=None, exc_kw=None, tags=None, is_active=True):
        self.name = name
        self.included_keywords = inc_kw if inc_kw else set()
        self.excluded_keywords = exc_kw if exc_kw else set()
        self.tags = tags if tags else set()
        self.active = is_active

    def add_keyword(self, keyword_name, to_include):
        if not isinstance(to_include, bool):
            raise scraper_utils.NewsScrapperError(
                "Parameter to_include in add_keyword() is invalid: '%s'"
                % repr(to_include)
            )

        if to_include:
            self.included_keywords.add(keyword_name)
        else:
            self.excluded_keywords.add(keyword_name)

    def __repr__(self):
        return (
            "\n"
            "------- <Scraping Rule> -------\n"
            "[Name]   : {rule_obj.name}\n"
            "[Include]: {rule_obj.included_keywords}\n"
            "[Exclude]: {rule_obj.excluded_keywords}\n"
            "[Tags]   : {rule_obj.tags}\n"
            "------------------------------\n"
            .format(rule_obj=self)
        )

    def __str__(self):
        return "<ScrapingRule '%s'>" % self.name

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.name == other.name and
            self.included_keywords == other.included_keywords and
            self.excluded_keywords == other.excluded_keywords and
            self.tags == other.tags
        )

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        # __eq__ makes this object unhashable
        # set() is also unhashable
        return hash(
            (  # tuple of attributes
                self.name,
                frozenset(self.included_keywords),
                frozenset(self.excluded_keywords),
                frozenset(self.tags)
            )
        )
