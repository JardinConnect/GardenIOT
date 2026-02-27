import time

class BaseSensor:
    def __init__(self, name, pin=None, **kwargs):
        self.name = name
        self.pin = pin
        self._last_reading = None
        self._last_read_time = 0
        self._read_interval = kwargs.get('read_interval', 2)
        self._error_count = 0

    def read(self, force=False):
        """Template Method : ne pas surcharger"""
        if not force and not self._should_read():
            return self._last_reading
        try:
            raw_data = self._read_raw()
        except Exception as e:
            self._error_count += 1
            print(f"  ✗ [{self.name}] Read error ({self._error_count}x): {e}")
            return self._last_reading

        if raw_data is None:
            self._error_count += 1
            print(f"  ✗ [{self.name}] No data returned ({self._error_count}x)")
            return self._last_reading

        if not self._validate(raw_data):
            self._error_count += 1
            print(f"  ✗ [{self.name}] Invalid data ({self._error_count}x): {raw_data}")
            return self._last_reading

        self._error_count = 0
        self._last_reading = {'sensor': self.name, 'data': raw_data}
        self._last_read_time = time.time()
        return self._last_reading

    def _read_raw(self):
        raise NotImplementedError

    def _validate(self, data):
        raise NotImplementedError

    def _should_read(self):
        return (time.time() - self._last_read_time) >= self._read_interval