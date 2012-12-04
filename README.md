TentRSS
=======

Script to show public [Tent](https://tent.io/) status posts as an RSS feed.

Based on [Flask](http://flask.pocoo.org/).
See Flask's install instructions to get this running.
TentRSS also uses [Requests](http://python-requests.org/) to fetch URLs
and [BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/)
to parse HTML (for finding HTML `<link>` tags).

Finally, to run this in production you should install
memcached and [pylibmc](http://pypi.python.org/pypi/pylibmc)
which is used to cache the latest posts for a few minutes.
Without pylibmc, Flask's SimpleCache will be used,
which is intended only for development.

Follow the author on Tent: https://scott.mn

Example nginx proxy configuration
---------------------------------

    location /tentrss/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_redirect default;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_set_header X-Original-Request-URI $request_uri;
    }

The X-Original-Request-URI header allows TentRSS to generate a correct
URL to the resulting feed.
