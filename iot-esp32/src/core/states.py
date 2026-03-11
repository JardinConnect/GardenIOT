"""
State Pattern - Device lifecycle states.
Each state encapsulates its own behavior and defines transitions.

State flow:
    BOOT -> PAIRING -> ACTIVE -> SLEEP -> ACTIVE
                        |
                      ERROR -> ACTIVE (recovery)
"""

import time


class DeviceState:
    """
    Base class for all device states.
    Subclasses implement handle() with state-specific behavior.
    """
    
    name = "UNKNOWN"
    
    def enter(self, context):
        """Called when entering this state"""
        print(f"[State] Entering {self.name}")
        context.event_bus.publish('state.changed', {
            'state': self.name
        })
    
    def handle(self, context):
        raise NotImplementedError
    
    def exit(self, context):
        """Called when leaving this state"""
        pass


class BootState(DeviceState):
    """
    Boot state: check pairing and transition.
    Hardware is already initialized by DeviceManager.initialize()
    """
    
    name = "BOOT"
    
    def handle(self, context):
        print("[BootState] Checking system status...")
        
        try:
            parent_id = context.config.get('device.parent_id')
            
            if parent_id:
                print(f"[BootState] Already paired with {parent_id}")
                context.set_state(ActiveState())
            else:
                print("[BootState] No parent_id, entering pairing mode")
                context.set_state(PairingState())
        
        except Exception as e:
            print(f"[BootState] Error: {e}")
            context.set_state(ErrorState(error=e, origin="BOOT"))


class PairingState(DeviceState):
    """
    Pairing state: wait for gateway pairing via LoRa.
    """
    
    name = "PAIRING"
    
    def handle(self, context):
        pairing_config = context.config.get('pairing', {})
        timeout_ms = pairing_config.get('timeout_ms', 5000)
        max_attempts = 3
        
        print(f"[PairingState] Starting pairing (timeout={timeout_ms}ms)")
        
        for attempt in range(1, max_attempts + 1):
            print(f"[PairingState] Attempt {attempt}/{max_attempts}...")
            
            pair_message = {
                'type': 'PAIR',
                'datas': f"UID:{context.uid}"
            }
            
            context.communication.send(pair_message, expect_ack=False)
            
            response = context.communication.receive(timeout_ms=timeout_ms)
            
            if response and response.get('type') == 'PAIR_ACK':
                parent_id = response.get('uid')
                context.config.set('device.parent_id', parent_id)
                context.config.save()
                print(f"[PairingState] Paired with gateway: {parent_id}")
                context.set_state(ActiveState())
                return
            
            print(f"[PairingState] No response, retrying...")
            time.sleep(1)
        
        print("[PairingState] Pairing failed after all attempts")
        context.set_state(ErrorState(error="Pairing timeout", origin="PAIRING"))


class ActiveState(DeviceState):
    """
    Active state: delegates to DeviceManager.run_cycle()
    """
    
    name = "ACTIVE"
    
    def __init__(self):
        self._consecutive_failures = 0
        self._max_failures = 3
    
    def handle(self, context):
        print("[ActiveState] Running cycle...")
        
        try:
            # Use run_cycle() which already does everything:
            # read sensors -> process -> send -> listen
            context.run_cycle()
            self._consecutive_failures = 0
            
            # After cycle, go to sleep to save power
            context.set_state(SleepState())
        
        except Exception as e:
            print(f"[ActiveState] Error: {e}")
            self._consecutive_failures += 1
            
            if self._consecutive_failures >= self._max_failures:
                print(f"[ActiveState] Too many failures ({self._consecutive_failures})")
                context.set_state(ErrorState(error=e, origin="ACTIVE"))
            else:
                # Sleep and retry
                context.set_state(SleepState())


class SleepState(DeviceState):
    """
    Sleep state: conserve power between reading cycles.
    """
    
    name = "SLEEP"
    
    def handle(self, context):
        interval = context.config.get('power.sleep_interval', 15)
        
        print(f"[SleepState] Sleeping {interval}s...")
        
        try:
            try:
                from machine import lightsleep
                lightsleep(interval * 1000)
            except ImportError:
                time.sleep(interval)
        except Exception as e:
            print(f"[SleepState] Sleep interrupted: {e}")
        
        # Wake up -> back to active
        context.set_state(ActiveState())


class ErrorState(DeviceState):
    """
    Error state: attempt recovery.
    """
    
    name = "ERROR"
    
    def __init__(self, error=None, origin=None):
        self.error = error
        self.origin = origin
        self._recovery_attempts = 0
        self._max_recovery = 3
    
    def enter(self, context):
        super().enter(context)
        print(f"[ErrorState] Error from {self.origin}: {self.error}")
        
        context.event_bus.publish('device.error', {
            'error': str(self.error),
            'origin': self.origin,
            'attempt': self._recovery_attempts
        })
    
    def handle(self, context):
        self._recovery_attempts += 1
        
        print(f"[ErrorState] Recovery attempt {self._recovery_attempts}/{self._max_recovery}...")
        
        if self._recovery_attempts > self._max_recovery:
            print("[ErrorState] Max recovery attempts reached, rebooting...")
            self._reboot(context)
            return
        
        wait_time = min(2 ** self._recovery_attempts, 30)
        print(f"[ErrorState] Waiting {wait_time}s before retry...")
        time.sleep(wait_time)
        
        try:
            if self.origin == "PAIRING":
                context.set_state(PairingState())
            else:
                context.set_state(ActiveState())
        except Exception as e:
            print(f"[ErrorState] Recovery failed: {e}")
    
    def _reboot(self, context):
        """Attempt hardware reboot"""
        print("[ErrorState] Rebooting device...")
        try:
            from machine import reset
            reset()
        except ImportError:
            print("[ErrorState] machine.reset() not available")
            self._recovery_attempts = 0
            context.set_state(BootState())