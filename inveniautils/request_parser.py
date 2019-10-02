import datetime
import json

from dateutil import parser


class RequestEncoder(json.JSONEncoder):
    def default(self, obj):
        encoded = None
        if isinstance(obj, datetime.datetime):
            encoded = {'_type': 'datetime', 'value': obj.isoformat()}
        else:
            # Let the base class default method raise the TypeError
            encoded = json.JSONEncoder.default(self, obj)

        return encoded


class RequestDecoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(
            self, object_hook=self.object_hook, *args, **kwargs
        )

    def object_hook(self, obj):
        decoded = obj
        if '_type' in obj:
            if obj['_type'] == 'datetime':
                decoded = parser.parse(obj['value'])

        return decoded
