import re
from dataclasses import dataclass


@dataclass
class Note:
    """Base class for various notes. Contains the mechanics for some regex matching of the contents

    Attributes
    ----------
    id : str
        id of the transaction to associate the Note with
    note : str
        content of the note
    """

    id: str
    note: str

    def __post_init__(self):
        if hasattr(self, 'regex'):
            self.match()

    def match(self):
        try:
            match = self.regex.match(self.note)
        except AttributeError:
            pass
        else:
            try:
                for key in match.groupdict():
                    setattr(self, key, match.group(key))
            except AttributeError as e:
                raise AttributeError(f'note \'{self.note}\' doesn\'t match {self.regex}')


@dataclass
class Link(Note):
    _tag: str = 'link'
    regex: re.Pattern = re.compile(f'{_tag}: ' + '(?P<target>[\d\w]+)$')


@dataclass
class Category(Note):
    _tag: str = 'cat'
    regex: re.Pattern = re.compile(f'{_tag}: ' + '(?P<category>.*)$')