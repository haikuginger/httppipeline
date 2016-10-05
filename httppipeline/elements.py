from json import loads as json_loads, dumps as json_dumps

from six.moves.urllib.parse import urlencode
from urllib3.util.url import Url, parse_url
from urllib3 import PoolManager

from httppipeline.base import HttpPipelineElement

class VarArgMerger(HttpPipelineElement):

    def __init__(self, *relevant_var_names, **kw):
        self.target_var = kw.pop('target_var', None) or self.target_var
        self.arg_names = relevant_var_names
        if self.target_var is None:
            raise TypeError('target_var must be a string.')
        super(VarArgMerger, self).__init__()

    def apply(self, context, **kwargs):
        target_var_val = kwargs.pop(self.target_var, {})
        new_value = {name: kwargs.pop(name) for name in self.arg_names if name in kwargs}
        target_var_val.update(new_value)
        kwargs[self.target_var] = target_var_val
        return kwargs


class CustomHeaderElement(VarArgMerger):

    target_var = 'headers'


class CustomQueryElement(VarArgMerger):

    target_var = 'url_query'


class CustomFormFieldElement(VarArgMerger):

    target_var = 'http_form'


class CustomUrlTemplateElement(VarArgMerger):

    target_var = 'url_template'


class UrlHandlingElement(HttpPipelineElement):

    def apply(self, context, url, **kwargs):
        url = url.format(**kwargs.get('url_template', {}))
        parsed_url = parse_url(url)
        existing_query = parsed_url.query or ''
        new_query = urlencode(kwargs.get('url_query', {}))
        if new_query and existing_query:
            final_query = '?'.join(existing_query, new_query)
        else:
            # Truthiness is great.
            final_query = new_query or existing_query
        fragment = parsed_url.fragment or kwargs.get('fragment', '')
        url = Url(*parsed_url[:5], final_query, fragment).url
        kwargs['url'] = url

        return kwargs


class FieldHandlingElement(HttpPipelineElement):

    BODY_METHODS = (
        'POST',
        'PUT',
        'PATCH',
    )

    def apply(self, context, fields=None, **kwargs):
        if fields is None:
            return
        elif kwargs.get('method', 'GET') in self.BODY_METHODS:
            kwargs.setdefault('http_form', {})
            kwargs['http_form'].update(fields)
        else:
            kwargs.setdefault('url_query', {})
            kwargs['url_query'].update(fields)

        return kwargs


class HttpFormBodyEncodingElement(HttpPipelineElement):

    def apply(self, context, http_form=None, body=None, **kwargs):
        if not http_form:
            return
        if body is not None:
            raise Exception('Cannot include both form fields and a POST body')
        else:
            kwargs['body'] = urlencode(http_form).encode('ascii')
            kwargs.setdefault('headers', {})
            kwargs['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
        return kwargs


class JsonCodingElement(HttpPipelineElement):

    def apply(self, context, json=None, **kwargs):
        if json is None:
            return
        kwargs['body'] = json_dumps(json).encode('utf-8')
        kwargs.setdefault('headers', {})
        kwargs['headers']['Content-Type'] = 'application/json'
        return kwargs

    def resolve(self, context, response):
        print(response)
        if response.headers.get('Content-Type') == 'application/json':
            return json_loads(response.data.decode('utf-8'))

class Urllib3RequestElement(HttpPipelineElement):

    def __init__(self, *args, **kwargs):
        self.pm = PoolManager(*args, **kwargs)
        super(Urllib3RequestElement, self).__init__()

    def apply(self, context, **kwargs):
        return self.pm.urlopen(**kwargs)
