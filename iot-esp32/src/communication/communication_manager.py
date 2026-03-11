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
        self._strategy = primary_strategy
        self._fallback = fallback_strategy
        name = primary_strategy.name if primary_strategy else 'None'
        print(f"[CommunicationManager] Primary: {name}")

    def set_strategy(self, strategy):
        print(f"[CommunicationManager] Switching to: {strategy.name}")
        self._strategy = strategy

    def set_fallback(self, fallback_strategy):
        self._fallback = fallback_strategy
        print(f"[CommunicationManager] Fallback set: {fallback_strategy.name}")

    def send(self, data, expect_ack=False):
        """
        Send data using active strategy with fallback support.
        
        Args:
            data: dict avec 'type' et 'datas'
            expect_ack: attendre un ACK
            
        Returns:
            bool: True si envoyé avec succès
        """
        if not self._strategy:
            print("[CommunicationManager] No strategy configured")
            return False
        
        try:
            success = self._strategy.send(data, expect_ack=expect_ack)
            
            if success:
                return True
            
            if self._fallback:
                print(f"[CommunicationManager] Primary failed, fallback: {self._fallback.name}")
                return self._fallback.send(data, expect_ack=expect_ack)
            
            return False
        
        except Exception as e:
            print(f"[CommunicationManager] Send error: {e}")
            
            if self._fallback:
                try:
                    return self._fallback.send(data, expect_ack=expect_ack)
                except Exception as e2:
                    print(f"[CommunicationManager] Fallback error: {e2}")
            
            return False

    def receive(self, timeout_ms=None):
        """
        Receive data using active strategy.
        
        Args:
            timeout_ms: timeout en millisecondes
            
        Returns:
            dict: message parsé ou None
        """
        if not self._strategy:
            print("[CommunicationManager] No strategy configured")
            return None
        
        try:
            return self._strategy.receive(timeout_ms=timeout_ms)
        except Exception as e:
            print(f"[CommunicationManager] Receive error: {e}")
            return None

    def disconnect(self):
        """Déconnecte tous les protocoles."""
        if self._strategy:
            try:
                self._strategy.disconnect()
            except Exception as e:
                print(f"[CommunicationManager] Disconnect error: {e}")
        
        if self._fallback:
            try:
                self._fallback.disconnect()
            except Exception as e:
                print(f"[CommunicationManager] Fallback disconnect error: {e}")

    def get_stats(self):
        """Get statistics from all strategies."""
        stats = {}
        
        if self._strategy:
            stats['primary'] = {
                'protocol': self._strategy.name,
                'stats': self._strategy.get_stats()
            }
        
        if self._fallback:
            stats['fallback'] = {
                'protocol': self._fallback.name,
                'stats': self._fallback.get_stats()
            }
        
        return stats