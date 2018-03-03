"""
"""

# Standard library
import datetime
# Local modules
import scraper_utils
from scraper_models import ScrapingRule


class ScrapingRuleFormatError(scraper_utils.NewsScrapperError):
    pass


def _extract_name_from_rule_statement(line, syntax):
    return line.replace(syntax, '').strip()


def get_rules_from_file(filename):

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

    rules_from_file = get_rules_from_file('test.rule')

    print(set(rules_from_file) == set(rules_from_db))
