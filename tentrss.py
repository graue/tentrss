import re
from flask import Flask, request as flask_request
import requests
app = Flask(__name__)


tent_mime = 'application/vnd.tent.v0+json'


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

        headers = {'accept': tent_mime}
        try:
            r = requests.get(href, timeout=5, headers=headers)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception loading %s: %s' % (href, repr(e)))
            continue

        # profile link worked, use it
        apiroots = r.json['https://tent.io/types/info/core/v0.1.0']['servers']
        break

    if apiroots is None or len(apiroots) == 0:
        return "No API roots found!"

    args = {'limit': '10',
            'post_types': 'https://tent.io/types/post/status/v0.1.0'}
    headers = {'accept': tent_mime}
    posts = None
    for root in apiroots:
        url = root + "/posts"
        try:
            r = requests.get(url, timeout=5, headers=headers, params=args)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception when getting %s: %s' % (url, repr(e)))
            continue

        posts = r.json
        if posts is None:
            app.logger.debug('%s returned no valid JSON' % url)
        else:
            break

    return "posts: %s" % repr(posts)

if __name__ == '__main__':
    app.run()
