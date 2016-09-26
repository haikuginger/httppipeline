from uuid import uuid4

import six

def has_callable_attr(obj, attr_name):
    return hasattr(obj, attr_name) and hasattr(getattr(obj, attr_name), '__call__')

class HttpPipelineElementMeta(type):

    def __init__(cls, name, bases, dct):
        if not (
            any(
                method in dct and hasattr(dct[method], '__call__') for method in ('apply', 'extract')
            )
            or (
                name == 'HttpPipelineElement' and bases == (object,)
            )
        ):
            raise TypeError(
                'HttpPipelineElement subclasses must have at least '
                'one callable method named \'apply\' or \'extract\'.'
            )
        super(HttpPipelineElementMeta, cls).__init__(name, bases, dct)

@six.add_metaclass(HttpPipelineElementMeta)
class HttpPipelineElement(object):
    
    def __init__(self):
        self.id = uuid4().hex

    def save_context(self, context, key, value):
        context.setdefault(self.id, {})
        context[self.id][key] = value

    def get_context(self, context, key, default=None):
        return context.get(self.id, {}).get(key, default)

class HttpPipeline(object):

    def __init__(self, *args):
        if not all(isinstance(each, HttpPipelineElement) for each in args):
            raise TypeError(
                'All elements passed to HttpPipeline must be '
                'subclasses of HttpPipelineElement'
            )
        self.steps = args

    def apply_steps(self):
        for each in self.steps:
            if has_callable_attr(each, 'apply'):
                yield each.apply

    def extract_steps(self):
        for each in self.steps[::-1]:
            if has_callable_attr(each, 'extract'):
                yield each.extract

    def request(self, **kwargs):
        for each in self.apply_steps():
            kwargs = each(**kwargs)

        resp = kwargs['request_method'](**kwargs['request'])

        for each in self.extract_steps():
            resp = each(resp)

        return resp
