import random
from datetime import datetime
# PyPI
import pytz
from psycopg2 import IntegrityError
# Local modules
from db_operation_api.mydb import PostgreSqlDB


class NewsDatabaseAPI(object):
    def __init__(self, conn, table_prefix=""):
        self.conn = conn
        self.table_prefix = table_prefix

    def store_a_scraping_rule_to_db(self, rule):

        if not isinstance(rule, ScrapingRule):
            raise RuntimeError(
                "Parameter 'rule' (%s) should be an instance of ScrapingRule"
                % repr(rule)
            )

        self._insert_data_into_table("scrapingrule", name=rule.name, active=True)
        rule_id = self._get_id_field_from_db("scrapingrule", name=rule.name)

        for tag in rule.tags:
            self._store_a_tag_to_db(tag, rule_id)
            self._insert_data_into_table("newscategory", name=tag)

        for keyword in rule.included_keywords:
            self._store_a_keyword_to_db(keyword, to_include=True, rule_id=rule_id)

        for keyword in rule.excluded_keywords:
            self._store_a_keyword_to_db(keyword, to_include=False, rule_id=rule_id)

    def store_a_rss_news_entry_to_db(self, news):

        if not isinstance(news, NewsRSSEntry):
            raise RuntimeError(
                "Parameter 'news' (%s) should be an instance of NewsRSSEntry"
                % repr(news)
            )
        curr_time = datetime.now(pytz.utc)
        self._insert_data_into_table(
            "newsdata",
            title=news.title,
            url=news.link,
            content=news.description,
            time=news.published_time,
            creation_time=curr_time,
            last_modified_time=curr_time
        )
        for rule in news.rule_score_map:
            self._setup_news_rule_relationship(news, rule)

    def _setup_news_rule_relationship(self, news, rule):

        news_id = self._get_id_field_from_db("newsdata", url=news.link)
        rule_id = self._get_id_field_from_db("scrapingrule", name=rule.name)

        self._insert_data_into_table(
            "newsdata_rules", newsdata_id=news_id, scrapingrule_id=rule_id
        )

        self._insert_data_into_table(
            "scoremap",
            news_id=news_id,
            rule_id=rule_id,
            weight=news.rule_score_map[rule]
        )

    def _store_a_keyword_to_db(self, keyword_name, to_include, rule_id):
        # Insert keyword to table
        self._insert_data_into_table(
            "newskeyword", name=keyword_name, to_include=to_include
        )
        # Get id of the newly inserted entry
        keyword_id = self._get_id_field_from_db(
            "newskeyword", name=keyword_name, to_include=to_include
        )
        # Setup relationship to ScrapingRule
        self._insert_data_into_table(
            "scrapingrule_keywords",
            scrapingrule_id=rule_id,
            newskeyword_id=keyword_id
        )

    def _store_a_tag_to_db(self, tag_name, rule_id):
        self._insert_data_into_table("newscategory", name=tag_name)
        tag_id = self._get_id_field_from_db(
            "newscategory", name=tag_name
        )
        self._insert_data_into_table(
            "scrapingrule_tags",
            scrapingrule_id=rule_id,
            newscategory_id=tag_id
        )

    def _get_id_field_from_db(self, table_name, **kwargs):
        table_name = self._add_table_name_prefix(table_name)
        rows = self.conn.get_field_by_conditions(table_name, "id", kwargs)
        if rows:
            return rows[0][0]
        else:
            raise RuntimeError(
                "Can not get entry id from table '{}' with condition {}."
                .format(table_name, kwargs)
            )

    def _insert_data_into_table(self, table_name, **kwargs):
        try:
            table_name = self._add_table_name_prefix(table_name)
            self.conn.insert_values_into_table(table_name, kwargs)
        except IntegrityError as e:
            if 'duplicate key value violates unique constraint' in str(e):
                print(str(e))
            else:
                raise

    def _add_table_name_prefix(self, table_name):
        return self.table_prefix + table_name


# For test
class ScrapingRule(object):
    def __init__(self, name):
        rand_num = str(random.randint(1, 100000))
        self.name = name + rand_num
        self.included_keywords = {'inc_kw' + rand_num, 'inc_kw' + rand_num}
        self.excluded_keywords = {'exc_kw' + rand_num, 'exc_kw' + rand_num}
        self.tags = {'AA' + rand_num, 'BBB' + rand_num, 'CC' + rand_num}

    def __str__(self):
        return "<ScrapingRule '%s'>" % self.name


class NewsRSSEntry(object):
    def __init__(
        self, title, desc, link, published_time, source, category=None, tags=None
    ):
        self.title = title
        self.description = desc
        self.link = link
        self.published_time = published_time
        self.source = source
        self.rule_score_map = {}
        self.tags = tags.copy() if tags else set()  # .copy() -> shallow copy

        if category:
            self.tags.add(category)

    def set_rules(self, rules):
        for rule in rules:
            score = self._compute_score_by_rule(rule)
            self.rule_score_map[rule] = score

    def _compute_score_by_rule(self, rule):
        return random.randint(1, 30)

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


if __name__ == "__main__":

    rand_num = str(random.randint(1, 100000))

    rule = ScrapingRule("Rule #" + rand_num)
    news = NewsRSSEntry(
        title="News #" + rand_num,
        desc="Description of News #" + rand_num,
        link="https://abc.cpm/" + rand_num,
        published_time=datetime.now(),
        source='Fake source',
        category='TESTING'
    )
    news.set_rules((rule,))

    with PostgreSqlDB(database="my_focus_news") as conn:
        d = NewsDatabaseAPI(conn, table_prefix="shownews_")
        d.store_a_scraping_rule_to_db(rule)
        d.store_a_rss_news_entry_to_db(news)
