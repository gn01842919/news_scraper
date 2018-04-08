"""This module provides tools to CRUD news_data and scraping_rules in the DB.

Example:
    with scraper_models.get_database(DATABASE_CONFIG) as conn:
        db_api = NewsDatabaseAPI(conn, table_prefix="my_focus_news")
        rules = db_api.get_scraping_rules()
        print(rules)

"""
import logging
from datetime import datetime
# PyPI
import pytz
from psycopg2 import IntegrityError
# Local modules
from scraper_models import NewsRSSEntry, ScrapingRule
import scraper_utils


class NewsDatabaseAPI(object):
    """This class provides APIs to manipulate models in the database.

    Args:
        conn (db_operation_api.mydb.MyDB): A database connection.

    """
    _table_prefix = "shownews_"

    def __init__(self, conn):
        self.conn = conn

    def get_news_data_and_setup_rule(self, scraping_rules):
        """Read news data from DB and set scraping_rules to them.

        Args:
            scraping_rules (Iterable(ScrapingRule)): Scraping_rules to decide
                whether each news is of interest.

        Returns:
            dict: A dict that maps id to a news
                <Key>: id filed of a news in the database.
                <Value>: An instance of ``NewsRSSEntry``.

        """
        rows = self.conn.get_fields_by_conditions(
            "shownews_newsdata",
            ("id", "title", "content", "url", "time",)
        )

        return {
            id: NewsRSSEntry(title, content, url, pub_time, '', rules=scraping_rules)
            for id, title, content, url, pub_time in rows
        }

    def get_scraping_rules(self):
        """Read scraping rules from DB.

        Returns:
            dict: A dict that maps id to a scraping rule.
                <Key>: id filed of a rule in the database.
                <Value>: An instance of ``ScrapingRule``.

        """
        if not self.conn.table_already_exists("shownews_scrapingrule"):
            scraper_utils.log_warning(
                "Table 'shownews_scrapingrule' does not exists in the database."
            )
            return {}

        rules_rows = self.conn.get_fields_by_conditions(
            "shownews_scrapingrule",
            ("*",)
        )

        rules_map = {
            rule_id: ScrapingRule(name=rule_name, is_active=is_active)
            for (rule_id, is_active, rule_name) in rules_rows
        }

        for rule_id, keyword_name, to_include in self._get_keywords_info():
            rules_map[rule_id].add_keyword(keyword_name, to_include)

        for rule_id, tag_name in self._get_tags_info():
            rules_map[rule_id].tags.add(tag_name)

        return rules_map

    def remove_all_rules_and_relations(self):
        """Remove all scraping rules and relationship with NewsData from DB.
        """
        # delete relationships
        self._reset_table("newsdata_rules")
        self._reset_table("scoremap")
        self._reset_table("scrapingrule_keywords")
        self._reset_table("scrapingrule_tags")
        # delete rules
        self._reset_table("newskeyword")
        self._reset_table("newscategory")
        self._reset_table("scrapingrule")

    def reset_news_data(self):
        """Remove all news data from DB.
        """
        self._reset_table("newsdata")

    def store_a_scraping_rule(self, rule):
        """Store a scraping rule into DB.

        Note that this only stores <rule, keywords, tags> into DB, and does
        not handle relationship with NewsRSSEntry.

        Args:
            rule (ScrapingRule): The scraping rule to store to DB.

        Raises:
            scraper_utils.NewsScrapperError: If ``rule`` is not instance of ScrapingRule.

        """

        if not isinstance(rule, ScrapingRule):
            raise scraper_utils.NewsScrapperError(
                "Parameter 'rule' (%s) should be an instance of ScrapingRule"
                % repr(rule)
            )

        self._insert_data_into_table("scrapingrule", name=rule.name, active=True)
        rule_id = self._get_id_field("scrapingrule", name=rule.name)

        for tag in rule.tags:
            self._store_a_tag(tag, rule_id)
            self._insert_data_into_table("newscategory", name=tag)

        for keyword in rule.included_keywords:
            self._store_a_keyword(keyword, to_include=True, rule_id=rule_id)

        for keyword in rule.excluded_keywords:
            self._store_a_keyword(keyword, to_include=False, rule_id=rule_id)

    def store_a_news_data(self, news):
        """Store a news to DB, and setup score and relationships with ScrapingRules.

        Note that scrapig rules should have exists in DB before this method is called.

        Args:
            news (NewsRSSEntry): The news to store to DB.

        Raises:
            scraper_utils.NewsScrapperError: If ``news`` is not instance of NewsRSSEntry.

        """
        if not isinstance(news, NewsRSSEntry):
            raise scraper_utils.NewsScrapperError(
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
            news_id = self._get_id_field("newsdata", url=news.link)
            rule_id = self._get_id_field("scrapingrule", name=rule.name)
            score = news.rule_score_map[rule]
            self.setup_news_rule_relationship(news_id, rule_id, score)

    def _get_keywords_info(self):
        keywords_query = (
            "SELECT rule_kw.scrapingrule_id, kw.name, kw.to_include "
            "FROM shownews_scrapingrule_keywords AS rule_kw "
            "INNER JOIN shownews_newskeyword AS kw "
            "ON rule_kw.newskeyword_id = kw.id;"
        )
        return self.conn.execute_sql_command(keywords_query)

    def _get_tags_info(self):
        tags_query = (
            "SELECT rule_tag.scrapingrule_id, tag.name "
            "FROM shownews_scrapingrule_tags AS rule_tag "
            "INNER JOIN shownews_newscategory AS tag "
            "ON rule_tag.newscategory_id = tag.id;"
        )
        return self.conn.execute_sql_command(tags_query)

    def setup_news_rule_relationship(self, news_id, rule_id, score):
        """Set up score and relationship between a news and a rule.
        """
        self._insert_data_into_table(
            "newsdata_rules",
            newsdata_id=news_id,
            scrapingrule_id=rule_id
        )

        self._insert_data_into_table(
            "scoremap",
            news_id=news_id,
            rule_id=rule_id,
            weight=score
        )

    def _store_a_keyword(self, keyword_name, to_include, rule_id):
        # Insert keyword to table
        self._insert_data_into_table(
            "newskeyword", name=keyword_name, to_include=to_include
        )
        # Get id from DB
        keyword_id = self._get_id_field(
            "newskeyword", name=keyword_name, to_include=to_include
        )
        # Setup relationship to ScrapingRule
        self._insert_data_into_table(
            "scrapingrule_keywords",
            scrapingrule_id=rule_id,
            newskeyword_id=keyword_id
        )

    def _store_a_tag(self, tag_name, rule_id):
        # Insert the tag
        self._insert_data_into_table("newscategory", name=tag_name)
        # Get id from DB
        tag_id = self._get_id_field(
            "newscategory", name=tag_name
        )
        # Setup relationship to ScrapingRule
        self._insert_data_into_table(
            "scrapingrule_tags",
            scrapingrule_id=rule_id,
            newscategory_id=tag_id
        )

    def _get_id_field(self, table_name, **kwargs):
        table_name = self._add_table_prefix(table_name)
        rows = self.conn.get_fields_by_conditions(table_name, ("id",), kwargs)
        if rows:
            return rows[0][0]
        else:
            raise scraper_utils.NewsScrapperError(
                "Can not get entry id from table '{}' with condition {}."
                .format(table_name, kwargs)
            )

    def _reset_table(self, table_name):
        table_name = self._add_table_prefix(table_name)
        self.conn.reset_table(table_name)

    def _insert_data_into_table(self, table_name, **kwargs):
        try:
            table_name = self._add_table_prefix(table_name)
            self.conn.insert_values_into_table(table_name, kwargs)
        except IntegrityError as err:
            if 'duplicate key value violates unique constraint' in str(err):
                logging.debug(str(err))
            else:
                raise

    def _update_table_entry(self, table_name, args_map, conditions):
        table_name = self._add_table_prefix(table_name)
        self.conn.update_table(table_name, args_map, conditions)

    def _add_table_prefix(self, table_name):
        return self._table_prefix + table_name
