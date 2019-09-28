import re
from dataclasses import dataclass

from .note import Note


@dataclass
class SplitNote(Note):
    _tag: str = 'split'
    regex: re.Pattern = re.compile(f'{_tag}: (?P<data>.*)$')

    def __post_init__(self):
        super().__post_init__()
        self.parts = [s.strip() for s in self.data.split(',')]
        self.parts = {self.parse_cat(s): Split.from_str(self.id, s) for s in self.parts}

    def relevant(self, test_category):
        return test_category in self.parts

    def modifier(self, category=None):
        return self.parts.get(category, 1)

    def parse_cat(self, input):
        try:
            # correctly processes categories with spaces in the name
            tokens = input.split(' ')
            if len(tokens) > 1:
                cat  = ' '.join(tokens[1:])
                return cat
            else:
                return
        except IndexError as e:
            return

    @property
    def cats(self):
        return list(self.parts.keys())


@dataclass
class Split:
    id: str
    match: re.Match

    @staticmethod
    def from_str(id, input):
        types = [SplitPercentage, SplitFraction, SplitAmount]
        for split_type in types:
            match = split_type.regex.search(input)
            if match is not None:
                return split_type(id, match)

    def modify(self, *args, **kwargs):
        raise NotImplementedError('Split class needs to implement a modify() method')


@dataclass
class SplitPercentage(Split):
    regex: re.Pattern = re.compile('(\d+)%')
    def __post_init__(self):
        self.value = int(self.match.group(1)) / 100

    def modify(self, val: float) -> float:
        return val * self.value


@dataclass
class SplitFraction(Split):
    regex: re.Pattern = re.compile('(?P<num>\d+)/(?P<denom>\d+)')
    def __post_init__(self):
        self.value = int(self.match.group('num')) / int(self.match.group('denom'))

    def modify(self, val: float) -> float:
        return val * self.value


@dataclass
class SplitAmount(Split):
    regex: re.Pattern = re.compile('-?\$?\d+(\.\d+)?')
    def __post_init__(self):
        self.value = float(self.match.group().replace('$', ''))

    def modify(self, value: float) -> float:
        return self.value