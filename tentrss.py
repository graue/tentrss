import re
from flask import Flask, request as flask_request
import requests
app = Flask(__name__)


@app.route('/')
def front_page():
    return 'TentRSS!'


@app.route('/feed')
def user_feed():
    tent_uri = flask_request.args.get('uri', '')
    app.logger.debug('tent_uri is %s' % tent_uri)
    if tent_uri == '':
        return 'No URI!'
    r = requests.get(tent_uri, timeout=5)

    # Look for profile links in the HTTP "link" header and get API roots
    # list from the first profile link that works.
    # TODO: Should also look for HTML "link" tag in response content
    apiroots = None
    for link in re.split(',\s*', r.headers['link']):
        href, rel = \
            re.match('''<(https?://[^>]+)>; rel="(https?://[^\"]+)"\s*$''',
                     link).groups()
        app.logger.debug('link: %s, rel=%s' % (href, rel))
        if rel != 'https://tent.io/rels/profile':
            continue

        headers = {'accept': 'application/vnd.tent.v0+json'}
        try:
            r = requests.get(href, timeout=5, headers=headers)
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception loading %s: %s' % (href, repr(e)))
            continue

        # profile link worked, use it
        apiroots = r.json['https://tent.io/types/info/core/v0.1.0']['servers']

    if apiroots is None:
        return "No API roots found!"

    return "API roots: %s" % repr(apiroots)

if __name__ == '__main__':
    app.run()
