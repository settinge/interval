from interval_processor import IntervalProcessor
from datetime import datetime


class IntervalData(IntervalProcessor):
    def __init__(self, data):
        super().__init__()
        self.record_start_date_time, self.record_end_date_time = self.process_time(
            data["record_start_date_time"], data["record_end_date_time"]
        )
        self.kwh = data["kwh"]
        self.cost = data["cost"]

    def process_time(self, end_time, start_time):
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%f%z")
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%f%z")
        return start_time.isoformat(), end_time.isoformat()
