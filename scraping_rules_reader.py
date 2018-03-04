"""
"""

# Standard library
import json
# Local modules
import scraper_utils
from scraper_models import ScrapingRule

OPTIONAL_ATTRIBUTES = ("exclude", "include", "tags")
ESSENTIAL_ATTRIBUTES = ("name",)


class ScrapingRuleFormatError(scraper_utils.NewsScrapperError):
    pass


def get_rules_from_file(filename):
    configs = _read_json_from_file(filename)

    for config in configs:
        name, included_kw, excluded_kw, tags = _get_attributes_from_config(config)
        yield ScrapingRule(
            name=name,
            inc_kw=set(included_kw),
            exc_kw=set(excluded_kw),
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
        rv = config[attr_name]

    except KeyError as e:
        attr_err = e.args[0]

        if attr_err in OPTIONAL_ATTRIBUTES:
            return list()

        elif attr_err in ESSENTIAL_ATTRIBUTES:
            raise ScrapingRuleFormatError("A rule must have 'name' attribute.")

        else:
            raise ScrapingRuleFormatError(
                "Attribute '%s' in the input file is unknown." % e.args[0]
            )

    if not isinstance(rv, expected_type):
        raise ScrapingRuleFormatError(
            "'%s' attribute must be instance of %s."
            % (attr_name, expected_type)
        )

    return rv


def _read_json_from_file(filename):
    try:
        with open(filename, 'r') as f:
            return json.loads(f.read())
    except FileNotFoundError as e:
        # Create an empty file
        scraper_utils.log_warning("File '%s' not found." % filename)
        return {}
    except json.decoder.JSONDecodeError as e:
        msg = "Fail to parse the content of file '%s' as JSON. " % filename
        scraper_utils.log_warning(msg)
        return {}


if __name__ == '__main__':  # For test
    import logging

    log_format = "[%(levelname)s] %(message)s\n"
    scraper_utils.setup_logger(
        'error_log',
        level=logging.WARNING,
        logfile='error.log',
        to_console=False,
        log_format=log_format
    )
    logging.basicConfig(level=logging.INFO, format=log_format)

    rules_from_file = get_rules_from_file('rule.json')
    print(tuple(rules_from_file))
