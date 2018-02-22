"""
"""
import scraper_utils


def set_rules_to_news_entries(news_entries, scraping_rules):
    for entry in news_entries:
        entry.set_rules(scraping_rules)


def get_target_news_by_scraping_rules(news_entries, scraping_rules):
    for news in news_entries:
        if news.total_score > 0:
            yield news


class NewsRSSEntry(object):
    def __init__(self, title, description, link, published_time, source, category=None, tags=None):
        self.title = title
        self.description = description
        self.link = link
        self.published_time = published_time
        self.source = source
        self.rule_score_map = {}  # rule ==> score, will be set in news_collector.py
        self.tags = tags.copy() if tags else set()  # .copy() -> shallow copy

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
            = 0 ==> others (not of interest)
        """
        score = 0

        for keyword in rule.excluded_keywords:
            if keyword in self.title:
                score -= 1

        # Skip 'included_keywords' if this news should be excluded
        if score >= 0:
            for keyword in rule.included_keywords:
                # Should change to analyse the content of the news
                if keyword in self.title:
                    score += 1

        return score

    def __repr__(self):
        return (
            "==== <NewsRSSEntry object at {}> ====\n"
            "  [Title]       : {}\n"
            "  [Description] : {}\n"
            "  [Link]        : {}\n"
            "  [Published]   : {}\n"
            "  [Source]      : {}\n"
            "  [Tags]        : {}\n"
            "  [Rules]       : {}\n"
            "=================================================\n"
            .format(
                hex(id(self)),
                self.title,
                self.description,
                self.link,
                self.published_time,
                self.source,
                self.tags,
                {str(rule): score for rule, score in self.rule_score_map.items()}
            )
        )

    def __str__(self):
        return "<NewsRSSEntry '%s'>" % self.title
