import dataclasses


@dataclasses.dataclass
class MyankipluginConfigSchema:
    @dataclasses.dataclass
    class Url:
        noteTypeId: int
        url: str

    urls: [Url]
