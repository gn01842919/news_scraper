"""This module contains tools to read scraping_rules from a file.

Attributes:
    ESSENTIAL_ATTRIBUTES (tuple(str)) Attributes that a rule must have.
    OPTIONAL_ATTRIBUTES (tuple(str)): Attributes that are optional.

"""
# Local modules
import scraper_utils
from scraper_models import ScrapingRule

ESSENTIAL_ATTRIBUTES = ("name",)
OPTIONAL_ATTRIBUTES = ("exclude", "include", "tags")


class ScrapingRuleFormatError(scraper_utils.NewsScrapperError):
    """Indicates that a rule has invalid format.
    """
    pass


def get_rules_from_file(filename):
    """Parse scraping rules from a file.

    Args:
        filename (str): File name of the rule file to parse.

    Yields:
        scraper_models.ScrapingRule: A scraping rule defined in the input file.

    Raises:
        ScrapingRuleFormatError: If a rule has invalid format.

    """
    configs = scraper_utils.read_json_from_file(filename)
    name_set = set()
    for config in configs:
        name, included_kw, excluded_kw, tags = _get_attributes_from_config(config)
        if name in name_set:
            raise ScrapingRuleFormatError("Rule names must be unique.")

        name_set.add(name)
        yield ScrapingRule(
            name=name,
            included_keywords=set(included_kw),
            excluded_keywords=set(excluded_kw),
            tags=set(tags)
        )


def _get_attributes_from_config(config):

    name = _get_attribute(config, "name", str)
    inc_kw = _get_attribute(config, "include", list)
    exc_kw = _get_attribute(config, "exclude", list)
    tags = _get_attribute(config, "tags", list)

    return name, inc_kw, exc_kw, tags


def _get_attribute(config, attr_name, expected_type):
    try:
        ret = config[attr_name]

    except KeyError as err:
        attr_err = err.args[0]

        if attr_err in OPTIONAL_ATTRIBUTES:
            return list()

        elif attr_err in ESSENTIAL_ATTRIBUTES:
            raise ScrapingRuleFormatError("A rule must have 'name' attribute.")

        else:
            raise ScrapingRuleFormatError(
                "Attribute '%s' in the input file is unknown." % err.args[0]
            )

    if not isinstance(ret, expected_type):
        raise ScrapingRuleFormatError(
            "'%s' attribute must be instance of %s."
            % (attr_name, expected_type)
        )

    return ret
