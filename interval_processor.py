from scraper_lib.converters import to_num
from scraper_lib.null import Null


class IntervalProcessor:
    """
    A Class that is expected to be inherited by each interval scraper

    Public API
    ----------
    data()
        returns a dictionary of all the data calling clients expect to receive

    update(dict)
        update the properties of the instance with the values in the given dict
    """

    __slots__ = ("record_start_date_time", "record_end_date_time", "kwh", "cost")

    def __init__(self):
        for slot in self.__slots__:
            setattr(self, slot, None)

    def __getitem__(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def update(self, dict):
        for key, value in dict.items():
            setattr(self, key, value)

    def clean_nums(self):
        num_types = ["kwh", "cost"]
        for attr in (slot for slot in self.__slots__ if slot in num_types):
            self[attr] = to_num(self[attr])
            if isinstance(self[attr], Null):
                self[attr] = 0.0

    def data(self):
        self.clean_nums()
        return {s: self[s] for s in self.__slots__}
