"""
Communication Manager - Strategy Pattern implementation.
Manages communication protocols with fallback support.
"""


class CommunicationManager:
    """
    Communication manager using Strategy Pattern.
    Allows changing protocols at runtime with automatic fallback.
    """

    def __init__(self, primary_strategy=None, fallback_strategy=None):
        """
        Initialize communication manager.
        
        Args:
            primary_strategy: main communication protocol
            fallback_strategy: backup protocol if primary fails
        """
        self._strategy = primary_strategy
        self._fallback = fallback_strategy
        print(f"[CommunicationManager] Primary: {primary_strategy.name if primary_strategy else 'None'}")

    def set_strategy(self, strategy):
        """
        Change the active communication strategy.
        
        Args:
            strategy: new CommunicationProtocol instance
        """
        print(f"[CommunicationManager] Switching to: {strategy.name}")
        self._strategy = strategy

    def set_fallback(self, fallback_strategy):
        """
        Set fallback strategy.
        
        Args:
            fallback_strategy: backup protocol
        """
        self._fallback = fallback_strategy
        print(f"[CommunicationManager] Fallback set: {fallback_strategy.name}")

    def send(self, data, expect_ack=None):
        """
        Send data using active strategy with fallback support.
        
        Args:
            data: data to send (dict or string)
            expect_ack: wait for acknowledgment (if protocol supports it)
            
        Returns:
            bool: True if sent successfully
        """
        if not self._strategy:
            print("[CommunicationManager] ✗ No strategy configured")
            return False
        
        try:
            # Try primary strategy
            success = self._strategy.send(data, expect_ack=expect_ack)
            
            if success:
                return True
            
            # Primary failed, try fallback
            if self._fallback:
                print(f"[CommunicationManager] Primary failed, using fallback: {self._fallback.name}")
                return self._fallback.send(data, expect_ack=expect_ack)
            
            return False
        
        except Exception as e:
            print(f"[CommunicationManager] ✗ Send failed via {self._strategy.name}: {e}")
            
            # Try fallback on exception
            if self._fallback:
                try:
                    print(f"[CommunicationManager] Falling back to {self._fallback.name}")
                    return self._fallback.send(data, expect_ack=expect_ack)
                except Exception as e2:
                    print(f"[CommunicationManager] ✗ Fallback also failed: {e2}")
            
            return False
    
    def receive(self, timeout_ms=None):
        """
        Receive data using active strategy.
        
        Args:
            timeout_ms: receive timeout in milliseconds
            
        Returns:
            dict or None: received message
        """
        if not self._strategy:
            print("[CommunicationManager] ✗ No strategy configured")
            return None
        
        try:
            return self._strategy.receive(timeout_ms=timeout_ms)
        except Exception as e:
            print(f"[CommunicationManager] ✗ Receive failed: {e}")
            return None
    
    def get_stats(self):
        """Get statistics from active strategy"""
        if not self._strategy:
            return {}
        
        stats = {
            'primary': {
                'protocol': self._strategy.name,
                'stats': self._strategy.get_stats() if hasattr(self._strategy, 'get_stats') else {}
            }
        }
        
        if self._fallback:
            stats['fallback'] = {
                'protocol': self._fallback.name,
                'stats': self._fallback.get_stats() if hasattr(self._fallback, 'get_stats') else {}
            }
        
        return stats