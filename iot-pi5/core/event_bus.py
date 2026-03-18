class EventBus:
    def __init__(self):
        self._listeners = {}  # {event_name: [callbacks]}

    def subscribe(self, event_name, callback):
        """S'abonne à un événement."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def publish(self, event_name, data=None):
        """Publie un événement."""
        if event_name in self._listeners:
            for callback in self._listeners[event_name]:
                callback(data)