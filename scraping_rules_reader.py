"""
"""

# Standard library
import datetime
# Local modules
import scraper_utils


class ScrapingRuleFormatError(scraper_utils.NewsScrapperError):
    pass


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


def _extract_name_from_rule_statement(line, syntax):
    return line.replace(syntax, '').strip()


def read_rules_from_db_connection(conn):
    if not conn.table_already_exists("shownews_scrapingrule"):
        scraper_utils.log_warning("Table 'shownews_scrapingrule' does not exists in the database.")
        return {}

    rules_query = "SELECT * FROM shownews_scrapingrule;"

    keywords_query = (
        "SELECT rule_kw.scrapingrule_id, kw.name, kw.to_include "
        "FROM shownews_scrapingrule_keywords AS rule_kw "
        "INNER JOIN shownews_newskeyword AS kw "
        "ON rule_kw.newskeyword_id = kw.id;"
    )

    tags_query = (
        "SELECT rule_tag.scrapingrule_id, tag.name "
        "FROM shownews_scrapingrule_tags AS rule_tag "
        "INNER JOIN shownews_newscategory AS tag "
        "ON rule_tag.newscategory_id = tag.id;"
    )

    rules_rows = conn.execute_sql_command(rules_query)
    keywords_rows = conn.execute_sql_command(keywords_query)
    tags_rows = conn.execute_sql_command(tags_query)

    rules_map = {}

    rules_map = {
        rule_id: ScrapingRule(name=rule_name, is_active=is_active)
        for (rule_id, is_active, rule_name) in rules_rows
    }

    for rule_id, keyword_name, to_include in keywords_rows:
        rules_map[rule_id].add_keyword(keyword_name, to_include)

    for (rule_id, tag_name) in tags_rows:
        rules_map[rule_id].tags.add(tag_name)

    return rules_map.values()


def read_rules_from_file(filename):

    rules = {}

    with open(filename, 'r') as f:

        curr_rule = None
        # for line in f.readlines():
        for line in f:
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            elif line.startswith('RULE'):
                if curr_rule is not None:
                    raise ScrapingRuleFormatError(
                        "curr_rule is not None before starting rule [%s]" % line
                    )

                rule_name = _extract_name_from_rule_statement(line, 'RULE')

                if not rule_name:
                    # Just to make sure that rule_name is unique when not provided
                    rule_name = str(datetime.datetime.now())

                elif rule_name in rules:  # rule_name should be unique
                    raise ScrapingRuleFormatError(
                        "Duplicate rule name [%s] is not allowed." % rule_name
                    )

                curr_rule = ScrapingRule(rule_name)

            elif curr_rule is None:
                raise ScrapingRuleFormatError(
                    "curr_rule is None when it should not be." % line
                )

            elif line == "END-OF-RULE":
                rules[rule_name] = curr_rule
                curr_rule = None

            elif line.startswith('INCLUDE'):
                keyword = _extract_name_from_rule_statement(line, 'INCLUDE')

                if not keyword:
                    raise ScrapingRuleFormatError(
                        "Keyword name in line [%s] can not be empty." % line
                    )

                curr_rule.included_keywords.add(keyword)

            elif line.startswith('EXCLUDE'):
                keyword = _extract_name_from_rule_statement(line, 'EXCLUDE')

                if not keyword:
                    raise ScrapingRuleFormatError(
                        "Keyword name in line [%s] can not be empty." % line
                    )

                curr_rule.excluded_keywords.add(keyword)

            elif line.startswith('TAG'):
                tag = _extract_name_from_rule_statement(line, 'TAG')

                if not tag:
                    raise ScrapingRuleFormatError(
                        "Tag name in line [%s] can not be empty." % line
                    )

                curr_rule.tags.add(tag)

            else:
                raise ScrapingRuleFormatError(
                    "Unrecognized syntax: [%s]." % line
                )

    if len(rules) <= 0:
        raise ScrapingRuleFormatError(
            "Warning: There are no scraping rules"
        )

    return rules.values()


if __name__ == '__main__':  # For test
    from db_operation_api.mydb import PostgreSqlDB
    with PostgreSqlDB(database="my_focus_news") as conn:
        rules_from_db = read_rules_from_db_connection(conn)

    rules_from_file = read_rules_from_file('test.rule')

    print(rules_from_db)
    print(rules_from_file)

    print(set(rules_from_file) == set(rules_from_db))
