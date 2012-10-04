import re
from datetime import datetime
from urlparse import urljoin
from flask import Flask, render_template, make_response, url_for, \
                  request as flask_request
import requests
app = Flask(__name__)


tent_mime = 'application/vnd.tent.v0+json'


def get_latest_posts(tent_uri):
    app.logger.debug('tent_uri is %s' % tent_uri)
    if tent_uri == '':
        return None, None, 'No URI!'
    try:
        r = requests.get(tent_uri, timeout=5)
    except requests.ConnectionError as e:
        app.logger.debug('Connection to %s failed: %s' % (tent_uri, repr(e)))
        return None, None, "Can't connect to %s" % tent_uri

    # Look for profile links in the HTTP "link" header and get API roots
    # list from the first profile link that works.
    # TODO: Should also look for HTML "link" tag in response content
    apiroots = None
    links = r.headers['link']
    if links is None or links == '':
        return None, None, 'Missing HTTP link header'
    for link in re.split(',\s*', links):
        pattern = '''<([^>]+)>; rel="(https?://[^\"]+)"\s*$'''
        try:
            href, rel = re.match(pattern, link).groups()
        except AttributeError:
            continue # try next link, this one didn't parse

        app.logger.debug('link: %s, rel=%s' % (href, rel))
        if rel != 'https://tent.io/rels/profile':
            continue

        # convert relative link (like "/profile") to absolute
        href = urljoin(tent_uri, href)

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
        return None, None, "No API roots found!"

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

    # prepare info the template needs
    for post in posts:
        # The protocol unfortunately does not give us a canonical URL for
        # opening a post in a web browser. We can come up with a URL that
        # that returns each individual post as raw JSON, but that's it.
        #
        # So, for user-friendliness use the JSON URL only as a GUID, but
        # not a link (it will try to download a JSON file). For the time
        # being at least, we will special-case https://username.tent.is/
        # entities and provide a link in those cases only.

        post['post_guid'] = root + '/posts/' + post['id']
        m = re.match('''https://(\w+)\.tent\.is/tent$''', root)
        if m is not None:  # This is a Tent.is user
            post['post_link'] = 'https://' + m.groups()[0] \
                              + '.tent.is/posts/' + post['id']

        dt = datetime.utcfromtimestamp(int(post['published_at']))
        # We don't know the actual timezone in which the user made this
        # post, but UNIX timestamps are UTC-based so we hardcode +0000.
        post['rfc822_time'] = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')

    return posts, root, None


@app.route('/')
def front_page():
    tent_uri = flask_request.args.get('uri', '')
    if tent_uri is None or tent_uri == '':
        return render_template('index.html')
    posts, root, error = get_latest_posts(tent_uri)

    if error is None:
        feed_url = urljoin(flask_request.host_url,
                           url_for('user_feed') + '?uri=' + tent_uri)
        return render_template('feed.html', posts=posts, uri=tent_uri,
                               root=root, feed_url=feed_url)

    return render_template('error.html', uri=tent_uri, error=error), 404


@app.route('/feed')
def user_feed():
    tent_uri = flask_request.args.get('uri', '')
    posts, root, error = get_latest_posts(tent_uri)

    if error is None:
        response = make_response(render_template('feed.xml',
                                                  posts=posts, uri=tent_uri,
                                                  root=root))
        response.mimetype = 'application/xml'
        return response

    return render_template('error.html', uri=tent_uri, error=error), 404

if __name__ == '__main__':
    app.run()
