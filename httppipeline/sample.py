from urllib3 import PoolManager

from httppipeline.base import HttpPipeline, DefinedPipeline, HttpPipelineElement, ReverseResponse

from httppipeline.elements import (
    CustomHeaderElement,
    CustomQueryElement,
    CustomFormFieldElement,
    CustomUrlTemplateElement,
    UrlHandlingElement,
    FieldHandlingElement,
    HttpFormBodyEncodingElement,
    JsonCodingElement,
    Urllib3RequestElement
)

class Fake503(object):
    code = 503
    def __repr__(self):
        return '<HttpResponse>: 503 code'

class Retry503Element(HttpPipelineElement):

    def __init__(self, max_retries=5):
        self.max_retries = 5
        super(Retry503Element, self).__init__()

    def apply(self, context, **kwargs):
        context.save('request_state', kwargs)
        return kwargs

    def resolve(self, context, response):
        completed_retries = context.get('retries', 1)
        if response.code == 503 and completed_retries <= self.max_retries:
            print('Retrying ({}/{}): {}'.format(completed_retries, self.max_retries, response))
            context.save('retries', completed_retries + 1)
            return ReverseResponse(context.get('request_state'))
        else:
            return response

class PrinterElement(HttpPipelineElement):

    def apply(self, context, **kwargs):
        print(kwargs)
        return kwargs

    def resolve(self, context, response):
        return response


class HttpBinPostJsonVerifier(HttpPipelineElement):

    def apply(self, context, **kwargs):
        context.save('initial_kwargs', kwargs.copy())
        kwargs = {
            'url': 'http://httpbin.org/post',
            'method': 'POST',
            'json': kwargs
        }
        return kwargs

    def resolve(self, context, response):
        original = context.get('initial_kwargs')
        if response['json'] == original:
            return 'They equal! \n{}'.format(original)
        else:
            return 'They don\'t equal.\n{}\n{}'.format(original, response['json'])


class JsonMangler(HttpPipelineElement):

    def apply(self, context, json=None, **kwargs):
        if json is not None:
            json['thingy'] = 'hehehe'
            kwargs['json'] = json
            return kwargs

class Raise503Element(HttpPipelineElement):

    def resolve(self, context, response):
        return Fake503()

class FakeErrorRetryPipeline(DefinedPipeline):
    elements = (
        Retry503Element(max_retries=2),
        PrinterElement,
        Raise503Element
    )

class RealHttpPipeline(DefinedPipeline):
    elements = (
        JsonCodingElement,
        FieldHandlingElement,
        UrlHandlingElement,
        HttpFormBodyEncodingElement,
        PrinterElement,
        Urllib3RequestElement,
    )

class JsonVerifierPipeline(DefinedPipeline):
    elements = (
        HttpBinPostJsonVerifier,
        RealHttpPipeline
    )


class ManglingJsonVerifierPipeline(DefinedPipeline):
    elements = (
        HttpBinPostJsonVerifier,
        JsonMangler,
        RealHttpPipeline
    )
