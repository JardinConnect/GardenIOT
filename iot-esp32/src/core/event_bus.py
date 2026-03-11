"""
Event Bus - Observer Pattern implementation.
Allows components to publish and subscribe to events without direct coupling.
"""


class EventBus:
    """
    Centralized event bus for publish-subscribe pattern.
    Decouples event publishers from subscribers.
    """
    
    def __init__(self):
        """Initialize event bus with empty subscriber lists"""
        self._subscribers = {}
        print("[EventBus] Initialized")
    
    def subscribe(self, event_type, callback):
        """
        Subscribe to an event type.
        
        Args:
            event_type: string identifier for the event (e.g., 'sensor.data')
            callback: function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        print(f"[EventBus] Subscribed to '{event_type}' ({len(self._subscribers[event_type])} subscribers)")
    
    def unsubscribe(self, event_type, callback):
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: event identifier
            callback: callback function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                print(f"[EventBus] Unsubscribed from '{event_type}'")
            except ValueError:
                pass
    
    def publish(self, event_type, data=None):
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: event identifier
            data: optional data to pass to subscribers
        """
        if event_type not in self._subscribers:
            return
        
        # Call all registered callbacks
        for callback in self._subscribers[event_type]:
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error in subscriber for '{event_type}': {e}")
    
    def get_subscribers_count(self, event_type=None):
        """
        Get number of subscribers.
        
        Args:
            event_type: specific event type, or None for all
            
        Returns:
            int: number of subscribers
        """
        if event_type:
            return len(self._subscribers.get(event_type, []))
        
        return sum(len(subs) for subs in self._subscribers.values())
    
    def list_events(self):
        """List all registered event types"""
        return list(self._subscribers.keys())
