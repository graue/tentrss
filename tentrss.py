import re
import urllib
from datetime import datetime
from urlparse import urljoin
from flask import Flask, render_template, make_response, url_for, \
                  request as flask_request
import requests
from bs4 import BeautifulSoup
app = Flask(__name__)


tent_mime = 'application/vnd.tent.v0+json'
tent_link_rel = 'https://tent.io/rels/profile'


def get_profile_links_from(response):
    """ Extract profile links from a Requests response. """
    profiles = []

    # Option 1: HTTP Link header.
    links = response.headers['link']
    if links is not None and links != '':
        for link in re.split(',\s*', links):
            pattern = '''<([^>]+)>; rel="(https?://[^\"]+)"\s*$'''
            try:
                href, rel = re.match(pattern, link).groups()
            except AttributeError:
                continue  # try next link. this one didn't parse

            if rel == tent_link_rel:
                profiles += [href]

    # Option 2: HTML <link> tag.
    soup = BeautifulSoup(response.content)
    links = soup.findAll('link', rel=tent_link_rel)
    profiles += [link['href'] for link in links]

    # Returned profiles are converted to absolute URLs.
    return [urljoin(response.url, href) for href in profiles]


def get_latest_posts(tent_uri):
    app.logger.debug('tent_uri is %s' % tent_uri)
    if tent_uri == '':
        return None, None, 'No URI!'
    try:
        response = requests.get(tent_uri, timeout=5)
    except requests.ConnectionError as e:
        app.logger.debug('Connection to %s failed: %s' % (tent_uri, repr(e)))
        return None, None, "Can't connect to %s" % tent_uri

    apiroots = None
    profiles = get_profile_links_from(response)
    if len(profiles) == 0:
        return None, None, 'No profile link found'

    for profile in profiles:
        headers = {'accept': tent_mime}
        try:
            response = requests.get(profile, timeout=5, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception loading %s: %s' % (profile, repr(e)))
            continue

        # profile link worked, use it
        apiroots = response \
            .json['https://tent.io/types/info/core/v0.1.0']['servers']
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


def generate_feed_url(entity_uri):
    """ Generate feed URL for the given Tent entity URI. """
    # Generating the correct full absolute URL, given proxying,
    # is hard! If proxying, this requires you add an
    # X-Original-Request-URI header to the proxy configuration.
    return urljoin(urljoin(flask_request.host_url,
                           flask_request.headers.get('X-Original-Request-URI',
                                                     '/')),
                   '.' + url_for('user_feed') + '?uri=' +
                   urllib.quote(entity_uri))


@app.route('/')
def front_page():
    tent_uri = flask_request.args.get('uri', '')
    if tent_uri is None or tent_uri == '':
        return render_template('index.html')
    posts, root, error = get_latest_posts(tent_uri)

    if error is None:
        feed_url = generate_feed_url(tent_uri)
        return render_template('feed.html', posts=posts, uri=tent_uri,
                               root=root, feed_url=feed_url)

    return render_template('error.html', uri=tent_uri, error=error), 404


@app.route('/feed')
def user_feed():
    tent_uri = flask_request.args.get('uri', '')
    posts, root, error = get_latest_posts(tent_uri)

    if error is None:
        feed_url = generate_feed_url(tent_uri)
        response = make_response(render_template('feed.xml', posts=posts,
                                                  uri=tent_uri, root=root,
                                                  feed_url=feed_url))
        response.mimetype = 'application/xml'
        return response

    return render_template('error.html', uri=tent_uri, error=error), 404

if __name__ == '__main__':
    app.run()
