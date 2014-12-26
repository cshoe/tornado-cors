# -*- coding: utf-8 -*-

import inspect
import logging
import re


from tornado.web import RequestHandler
from tornado_cors import custom_decorator

logger = logging.getLogger(__name__)


ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
ACCESS_CONTROL_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
ACCESS_CONTROL_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
ACCESS_CONTROL_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
ACCESS_CONTROL_ALLOW_METHODS = 'Access-Control-Allow-Methods'
ACCESS_CONTROL_MAX_AGE = 'Access-Control-Max-Age'


def _get_class_that_defined_method(meth):
    for cls in inspect.getmro(meth.__self__.__class__):
        if meth.__name__ in cls.__dict__: return cls
    return None


class CorsMixin(object):
    """
    Add CORS header support to a Tornado RequestHandler.
    """

    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOW_HEADERS = None
    CORS_EXPOSE_HEADERS = None
    CORS_ALLOW_METHODS = None
    CORS_CREDENTIALS = False
    CORS_MAX_AGE = 86400
    CORS_ORIGIN_WHITELIST = []
    CORS_ORIGIN_REGEX_WHITELIST = []

    def set_default_headers(self):
        origin = self.request.headers.get('Origin')
        if self.should_add_cors_headers(origin):
            logger.debug('Including %s header', ACCESS_CONTROL_ALLOW_ORIGIN)
            allow_origin = '*' if self.CORS_ALLOW_ALL_ORIGINS else origin
            self.set_header(ACCESS_CONTROL_ALLOW_ORIGIN, allow_origin)

            if self.CORS_CREDENTIALS == True:
                logger.debug('Including %s header', ACCESS_CONTROL_ALLOW_CREDENTIALS)
                self.set_header(ACCESS_CONTROL_ALLOW_CREDENTIALS, 'true')

            if self.CORS_EXPOSE_HEADERS != None:
                self.set_header('Access-Control-Expose-Headers',self.CORS_EXPOSE_HEADERS)

    @custom_decorator.wrapper
    def options(self, *args, **kwargs):
        logger.debug('Processing CORS preflight OPTIONS request')
        origin = self.request.headers.get('Origin')
        if self.should_add_cors_headers(origin):

            # always include methods
            logger.debug('Including %s header', ACCESS_CONTROL_ALLOW_METHODS)
            self.set_header(ACCESS_CONTROL_ALLOW_METHODS, self._get_methods())

            if self.CORS_ALLOW_HEADERS:
                logger.debug('Including %s header', ACCESS_CONTROL_ALLOW_HEADERS)
                self.set_header(ACCESS_CONTROL_ALLOW_HEADERS, self.CORS_ALLOW_HEADERS)

            if self.CORS_MAX_AGE:
                logger.debug('Including %s header', ACCESS_CONTROL_MAX_AGE)
                self.set_header(ACCESS_CONTROL_MAX_AGE, self.CORS_MAX_AGE)

            self.set_status(204)
            self.finish()
        else:
            super(CorsMixin, self).options(*args, **kwargs)

    def _get_methods(self):
        if self.CORS_ALLOW_METHODS != None:
            logger.debug('Using methods from handler CORS_METHOD setting')
            return self.CORS_ALLOW_METHODS

        logger.debug('Introspecting handler for method list')

        # CORS methods not explicitly set, introspect the handler and include
        # all HTTP verb related methods.
        supported_methods = [method.lower() for method in self.SUPPORTED_METHODS]
        methods = []
        for meth in supported_methods:
            instance_meth = getattr(self, meth)
            if not meth:
                continue
            handler_class = _get_class_that_defined_method(instance_meth)
            if not handler_class is RequestHandler:
                methods.append(meth.upper())

        return ", ".join(methods)

    def should_add_cors_headers(self, origin_header_val):
        """
        Indicate whether or not CORS headers should be supplied for a request
        from ``origin_header_val``.
        """
        thing = (origin_header_val is not None and
            (self._check_origin_whitelist(origin_header_val) or
            self.CORS_ALLOW_ALL_ORIGINS))
        return thing

    def _check_origin_whitelist(self, origin_header_val):
        """
        Check the Origin header value against a list of
        whitelisted origins and whitelisted origin regexes. Return ``True`` if
        the Origin is found, ``False`` if it is not.
        """
        return (origin_header_val in self.CORS_ORIGIN_WHITELIST or
                self._check_regex_origin_whitelist(origin_header_val))

    def _check_regex_origin_whitelist(self, origin_header_val):
        """
        Check the Origin header value against a whitelisted origin regexes.
        Return ``True`` if a match if found, ``False`` if not.
        """
        for domain_pattern in self.CORS_ORIGIN_REGEX_WHITELIST:
            if re.match(domain_pattern, origin_header_val):
                return True
