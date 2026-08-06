import re

from importlib.metadata import version

from tcrm.tools import parse_version


def patch_module():
    # Between these versions, data URLs in a style attribute / style node were stripped
    # incorrectly. The fix touches lxml.html.clean (removed / split out in newer lxml).
    v = parse_version(version("lxml"))
    if not (parse_version("4.6.0") <= v < parse_version("5.2.0")):
        return
    try:
        import lxml.html.clean as clean
    except ImportError:
        return
    clean._find_image_dataurls = re.compile(r"data:image/(.+?);base64,").findall
