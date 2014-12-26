# -*- coding: utf-8 -*-
import imp
import functools
import sys

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, asynchronous, RequestHandler

import tornado_cors as cors
from tornado_cors import custom_decorator


passed_by_custom_wrapper = False


def custom_wrapper(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        return result
    global passed_by_custom_wrapper
    passed_by_custom_wrapper = id(wrapper)
    return wrapper


class CustomWrapperTestCase(AsyncHTTPTestCase):

    def setUp(self):
        self.original_wrapper = custom_decorator.wrapper

    def tearDown(self):
        custom_decorator.wrapper = self.original_wrapper

    def test_wrapper_customization(self):
        version = sys.version_info[0]
        if version == 2:
            # assert default wrapper is being used
            wrapper_module_name = cors.CorsMixin.options.im_func.func_code.co_filename
            self.assertFalse(passed_by_custom_wrapper)
            self.assertTrue(wrapper_module_name.endswith("tornado/web.py"))

        self.assertEquals(cors.custom_decorator.wrapper, asynchronous)

        # overwrite using custom wrapper and reload module
        custom_decorator.wrapper = custom_wrapper
        imp.reload(cors)

        if version == 2:
            # assert new wrapper is being used
            wrapper_module_name = cors.CorsMixin.options.im_func.func_code.co_filename
            self.assertTrue(passed_by_custom_wrapper)
            self.assertTrue(wrapper_module_name.endswith("tests/test_tornado_cors.py"))

        self.assertEquals(cors.custom_decorator.wrapper, custom_wrapper)


class DefaultValuesTestCase(AsyncHTTPTestCase):
    """
    Tests a handler that implements all default CORS settings.
    """
    def test_no_origin_header_options_request(self):
        """
        When an ``Origin`` header is not included in the request, no
        ``Access-Control-*`` headers should be included.
        """
        self.http_client.fetch(self.get_url('/default'), self.stop, method='OPTIONS')
        headers = self.wait().headers

        self.assertNotIn(cors.ACCESS_CONTROL_ALLOW_ORIGIN, headers)
        self.assertNotIn(cors.ACCESS_CONTROL_ALLOW_HEADERS, headers)
        self.assertNotIn(cors.ACCESS_CONTROL_ALLOW_CREDENTIALS, headers)
        self.assertNotIn(cors.ACCESS_CONTROL_ALLOW_METHODS, headers)
        self.assertNotIn(cors.ACCESS_CONTROL_MAX_AGE, headers)

    def test_preflight_options_request(self):
        """
        Test sending an OPTIONS request to a handler with default CORS
        settings.
        """
        origin = DefaultValuesHandler.CORS_ORIGIN_WHITELIST[0]
        expected_methods = 'POST, DELETE, PUT, OPTIONS'
        self.http_client.fetch(self.get_url('/default'), self.stop, method='OPTIONS',
            headers={'Origin': origin})
        headers = self.wait().headers
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_ORIGIN], origin)
        self.assertEqual(int(headers[cors.ACCESS_CONTROL_MAX_AGE]), 86400)
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_METHODS], expected_methods)

        self.assertNotIn(cors.ACCESS_CONTROL_ALLOW_HEADERS, headers)
        self.assertNotIn(cors.ACCESS_CONTROL_ALLOW_CREDENTIALS, headers)
        self.assertNotIn(cors.ACCESS_CONTROL_EXPOSE_HEADERS, headers)

    def test_get_request(self):
        """
        Test sending a GET request to a handler with (mostly) default CORS
        settings.
        """
        origin = DefaultValuesHandler.CORS_ORIGIN_WHITELIST[0]
        self.http_client.fetch(self.get_url('/default'), self.stop, method='GET',
            headers={'Origin': origin})
        headers = self.wait().headers
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_ORIGIN], origin)

        self.assertNotIn(cors.ACCESS_CONTROL_ALLOW_CREDENTIALS, headers)
        self.assertNotIn(cors.ACCESS_CONTROL_EXPOSE_HEADERS, headers)

    def get_app(self):
        return Application([(r'/default', DefaultValuesHandler)])


class DefaultValuesHandler(cors.CorsMixin, RequestHandler):
    """
    One settings 'CORS_ORIGIN_WHITELIST' is not set to default in order
    to get the rest of the settings to function.
    """
    CORS_ORIGIN_WHITELIST = ['http://example.foo', ]

    @asynchronous
    def post(self):
        self.finish()

    @asynchronous
    def put(self):
        self.finish()

    @asynchronous
    def delete(self):
        self.finish()


class HasOptionsMethodTestCase(AsyncHTTPTestCase):
    """
    Tests a handler that implements it's own OPTIONS method that should be
    called on Non-CORS OPTIONS requests.
    """
    def test_options_request_with_no_origin(self):
        """
        This test hits a handler that has it's own ``options`` method without
        an ``Origin`` header. In this case, the non-preflight OPTIONS
        response should be returned.
        """
        self.http_client.fetch(self.get_url('/has_options_method'), self.stop,
            method='OPTIONS')
        body = self.wait().body
        self.assertIn('Non-CORS', body)

    def get_app(self):
        return Application([(r'/has_options_method', HasOptionsMethodHandler)])


class HasOptionsMethodHandler(cors.CorsMixin, RequestHandler):
    """
    CORS enabled can have their own OPTIONS methods. If they receive an OPTIONS
    request but no ``Origin`` header, the non-preflight OPTIONS method should
    respond.

    This handler allows the above case to be tested.
    """
    @asynchronous
    def options(self):
        self.write('Non-CORS OPTIONS responding')
        self.finish()


class CustomValuesTestCase(AsyncHTTPTestCase):
    """
    Test resposes from a handler that has custom settings.
    """
    def test_preflight_options_request(self):
        """
        Test sending a preflight OPTIONS request.
        """
        origin = CustomValuesHandler.CORS_ORIGIN_WHITELIST[0]
        self.http_client.fetch(self.get_url('/custom'), self.stop, method='OPTIONS',
            headers={'Origin': origin})
        headers = self.wait().headers
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_ORIGIN], origin)
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_METHODS],
            CustomValuesHandler.CORS_ALLOW_METHODS)

        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_HEADERS],
            CustomValuesHandler.CORS_ALLOW_HEADERS)
        self.assertEqual(headers[cors.ACCESS_CONTROL_EXPOSE_HEADERS],
            CustomValuesHandler.CORS_EXPOSE_HEADERS)
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_CREDENTIALS], 'true')

        self.assertNotIn('Access-Control-MaxAge', headers)

    def test_post_request(self):
        """
        Test sending a POST request.
        """
        origin = CustomValuesHandler.CORS_ORIGIN_WHITELIST[0]
        self.http_client.fetch(self.get_url('/custom'), self.stop, method='OPTIONS',
            headers={'Origin': origin})
        headers = self.wait().headers

        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_ORIGIN], origin)
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_CREDENTIALS], 'true')
        self.assertEqual(headers[cors.ACCESS_CONTROL_EXPOSE_HEADERS],
            CustomValuesHandler.CORS_EXPOSE_HEADERS)

    def get_app(self):
        return Application([(r'/custom', CustomValuesHandler)])


class CustomValuesHandler(cors.CorsMixin, RequestHandler):

    CORS_ORIGIN_WHITELIST = ['http://example.foo', ]
    CORS_ALLOW_HEADERS = 'Content-Length'
    CORS_EXPOSE_HEADERS = 'Content-Length'
    CORS_ALLOW_METHODS = 'POST'
    CORS_CREDENTIALS = True
    CORS_MAX_AGE = None

    @asynchronous
    def post(self):
        self.finish()

    @asynchronous
    def put(self):
        self.finish()

    @asynchronous
    def delete(self):
        self.finish()


class WhitelistTestCase(AsyncHTTPTestCase):
    """
    Test responses from a handler that has a ``CORS_ORIGIN_WHITELIST`` setting.
    """
    def test_whitelist_match(self):
        """
        Pass an origin header that is included in the whitelist.
        """
        origin = 'http://example.foo'
        self.http_client.fetch(self.get_url('/whitelist_handler'), self.stop,
            method='OPTIONS', headers={'Origin': origin})
        headers = self.wait().headers
        self.assertEqual(headers['Access-Control-Allow-Origin'], origin)
        self.assertEqual(headers['Access-Control-Allow-Methods'], 'GET, OPTIONS')

    def test_whitelist_miss(self):
        """
        Pass an origin header that is not included in the whitelist
        """
        origin = 'http://notwhitelisted.foo'
        self.http_client.fetch(self.get_url('/whitelist_handler'), self.stop,
            method='OPTIONS', headers={'Origin': origin})
        headers = self.wait().headers
        self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_whitelist_scheme_miss(self):
        """
        Pass an origin header for a domain that is whitelisted but a different
        URL scheme. In this case, the domain is whitelisted for https traffic
        but not plain http.
        """
        origin = 'http://nohttpexample.foo'
        self.http_client.fetch(self.get_url('/whitelist_handler'), self.stop,
            method='OPTIONS', headers={'Origin': origin})
        headers = self.wait().headers
        self.assertNotIn('Access-Control-Allow-Origin', headers)

    def get_app(self):
        return Application([(r'/whitelist_handler', WhitelistHandler)])


class WhitelistHandler(cors.CorsMixin, RequestHandler):
    """
    Handler that implements the ``CORS_ORIGIN_WHITELIST`` setting.
    """
    CORS_ORIGIN_WHITELIST = ['http://example.foo', 'https://example.foo',
        'https://nohttpexample.foo']
    CORS_CREDENTIALS = None
    CORS_MAX_AGE = None

    @asynchronous
    def get(self):
        self.finish()


class RegexWhitelistTestCase(AsyncHTTPTestCase):
    """
    Test responses from a handler that has a ``CORS_ORIGIN_REGEX_WHITELIST``
    setting.
    """
    def test_regex_whitelist_hit(self):
        """
        Pass an origin header that should be whitelisted by a set regex.
        """
        origin = 'http://example.foo'
        self.http_client.fetch(self.get_url('/regex_whitelist_handler'), self.stop,
            method='OPTIONS', headers={'Origin': origin})
        response = self.wait()
        self.assertEqual(response.code, 204)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_regex_whitelist_miss(self):
        """
        Pass an origin header that should not be whitelisted by a set regex.
        """
        origin = 'http://bad.foo'
        self.http_client.fetch(self.get_url('/regex_whitelist_handler'), self.stop,
            method='OPTIONS', headers={'Origin': origin})
        response = self.wait()
        self.assertTrue(response.code, 405)
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def get_app(self):
        return Application([(r'/regex_whitelist_handler', RegexWhitelistHandler)])

class RegexWhitelistHandler(cors.CorsMixin, RequestHandler):
    """
    Handler that implements the ``CORS_ORIGIN_REGEX_WHITELIST`` setting.
    """
    # allow CORS requets from both http and https at example.foo
    CORS_ORIGIN_REGEX_WHITELIST = ['http[s]?\://example\.foo', ]
    CORS_CREDENTIALS = None
    CORS_MAX_AGE = None

    @asynchronous
    def get(self):
        self.finish()


class CustomMethodTestCase(AsyncHTTPTestCase):
    """
    Test a handler with a custom HTTP method.
    """
    def test_preflight_options_method(self):
        """
        Test sending a preflight OPTIONS request.
        """
        origin = 'http://example.foo'
        self.http_client.fetch(self.get_url('/custom_method'), self.stop,
            method='OPTIONS', headers={'Origin': origin})
        headers = self.wait().headers
        self.assertEqual(headers[cors.ACCESS_CONTROL_ALLOW_METHODS],
            'OPTIONS, NEW_METHOD')

    def get_app(self):
        return Application([(r'/custom_method', CustomMethodValuesHandler)])


class CustomMethodValuesHandler(cors.CorsMixin, RequestHandler):

    CORS_ALLOW_ALL_ORIGINS = True
    SUPPORTED_METHODS = list(CustomValuesHandler.SUPPORTED_METHODS) + ["NEW_METHOD"]

    @asynchronous
    def new_method(self):
        self.finish()
