# helpers/site.py

import json
from pathlib import Path
import re


PANEL_ROOT = Path("/opt/panel")
SITES_DIR = PANEL_ROOT / "sites"


def domain_exists(domain):
    if not SITES_DIR.exists():
        return False

    for site in SITES_DIR.iterdir():
        config = site / "site.json"

        if not config.exists():
            continue

        with open(config) as f:
            data = json.load(f)

        if data.get("domain") == domain:
            return True

    return False


# validators.py

SITE_NAME_REGEX = r"^[a-zA-Z0-9_-]+$"
DOMAIN_REGEX = r"^[a-zA-Z0-9.-]+$"


def validate_site_name(name):
    return re.match(SITE_NAME_REGEX, name)


def validate_domain(domain):
    return re.match(DOMAIN_REGEX, domain)

# helpers/site.py

def port_exists(port):

    for site in SITES_DIR.iterdir():

        config = site / "site.json"

        if not config.exists():
            continue

        with open(config) as f:
            data = json.load(f)

        if data.get("port") == port:
            return True

    return False


def get_site(identifier):

    identifier = identifier.strip().lower()

    if not SITES_DIR.exists():
        return None

    for site in SITES_DIR.iterdir():

        config = site / "site.json"

        if not config.exists():
            continue

        try:

            with open(config) as f:
                data = json.load(f)

            #
            # MATCH NAME
            #

            if data.get("name") == identifier:
                return data

            #
            # MATCH DOMAIN
            #

            if data.get("domain") == identifier:
                return data

        except:
            continue

    return None