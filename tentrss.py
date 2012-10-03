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
    for link in re.split(',\s*', r.headers['link']):
        href, rel = \
            re.match('''<(https?://[^>]+)>; rel="(https?://[^\"]+)"\s*$''',
                     link).groups()
        app.logger.debug('link: %s, rel=%s' % (href, rel))
    return 'not done yet but worked so far!'

if __name__ == '__main__':
    app.run()
