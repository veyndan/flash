#! /usr/bin/env python

import config
import dataclasses
import json

default_config_schema = config.MyankipluginConfigSchema(
    urls=[
        config.MyankipluginConfigSchema.Url(
            noteTypeId=-1,
            url="https://www.example.com",
        )
    ]
)

config_as_json = json.dumps(dataclasses.asdict(default_config_schema), indent=2)

with open('config.json', 'w') as output:
    output.write(config_as_json + '\n')

# if __name__ == '__main__':
#     myankiplugin_config_schema = MyankipluginConfigSchema(
#         urls=[
#             MyankipluginConfigSchema.Url(
#                 noteTypeId=-1,
#                 url="https://www.example.com",
#             )
#         ]
#     )
#     to_json = json.dumps(dataclasses.asdict(myankiplugin_config_schema))
#
#
#     def object_hook(dct: dict):
#         if set(field.name for field in dataclasses.fields(MyankipluginConfigSchema.Url)) == dct.keys():
#             return MyankipluginConfigSchema.Url(**dct)
#         # if all(field.name in dct for field in dataclasses.fields(MyankipluginConfigSchema.Url)):
#         #     return MyankipluginConfigSchema.Url(**dct)
#         if all(field.name in dct for field in dataclasses.fields(MyankipluginConfigSchema)):
#             return MyankipluginConfigSchema(**dct)
#         print("invalid")
#         return dct
#
#
#     from_json = json.loads(to_json, object_hook=object_hook)
#     print(from_json)
