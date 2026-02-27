"""
State Pattern - Device lifecycle states.
Each state encapsulates its own behavior and defines transitions.

State flow:
    BOOT → PAIRING → ACTIVE → SLEEP → ACTIVE
                        ↓
                      ERROR → ACTIVE (recovery)
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
        print(f"[State] → Entering {self.name}")
        context.event_bus.publish('state.changed', {
            'state': self.name
        })
    
    def handle(self, context):
        """
        Execute state-specific behavior.
        
        Args:
            context: DeviceManager instance (access to all managers)
            
        Must call context.set_state() to transition.
        """
        raise NotImplementedError
    
    def exit(self, context):
        """Called when leaving this state"""
        pass


class BootState(DeviceState):
    """
    Boot state: initialize all hardware and managers.
    Transition → PairingState (if no parent_id)
    Transition → ActiveState (if already paired)
    """
    
    name = "BOOT"
    
    def handle(self, context):
        print("[BootState] Initializing system...")
        
        try:
            context.initialize()
            
            # Check if device is already paired
            parent_id = context.config.get('device.parent_id')
            
            if parent_id:
                print(f"[BootState] Already paired with {parent_id}")
                context.set_state(ActiveState())
            else:
                print("[BootState] No parent_id, entering pairing mode")
                context.set_state(PairingState())
        
        except Exception as e:
            print(f"[BootState] ✗ Init failed: {e}")
            context.set_state(ErrorState(error=e, origin="BOOT"))


class PairingState(DeviceState):
    """
    Pairing state: wait for gateway pairing via LoRa.
    Sends PAIR request, waits for PAIR_ACK with assigned parent_id.
    Transition → ActiveState (on successful pairing)
    Transition → ErrorState (on timeout)
    """
    
    name = "PAIRING"
    
    def handle(self, context):
        pairing_config = context.config.get('pairing', {})
        timeout_ms = pairing_config.get('timeout_ms', 5000)
        max_attempts = 3
        
        print(f"[PairingState] Starting pairing (timeout={timeout_ms}ms, max={max_attempts} attempts)")
        
        for attempt in range(1, max_attempts + 1):
            print(f"[PairingState] Attempt {attempt}/{max_attempts}...")
            
            # Send pairing request
            pair_message = {
                'type': 'PAIR',
                'datas': f"UID:{context.uid}"
            }
            
            context.communication.send(pair_message, expect_ack=False)
            
            # Listen for PAIR_ACK
            response = context.communication.receive(timeout_ms=timeout_ms)
            
            if response and response.get('type') == 'PAIR_ACK':
                parent_id = response.get('uid')
                
                # Save parent_id to config
                context.config.set('device.parent_id', parent_id)
                context.config.save()
                
                print(f"[PairingState] ✓ Paired with gateway: {parent_id}")
                context.set_state(ActiveState())
                return
            
            print(f"[PairingState] No response, retrying...")
            time.sleep(1)
        
        print("[PairingState] ✗ Pairing failed after all attempts")
        context.set_state(ErrorState(error="Pairing timeout", origin="PAIRING"))


class ActiveState(DeviceState):
    """
    Active state: read sensors, send data, listen for commands.
    This is the main operational state.
    Transition → SleepState (after data sent successfully)
    Transition → ErrorState (on repeated failures)
    """
    
    name = "ACTIVE"
    
    def __init__(self):
        self._consecutive_failures = 0
        self._max_failures = 3
    
    def handle(self, context):
        print("[ActiveState] Running cycle...")
        
        try:
            # Read sensors and send data
            success = context.send_sensor_data(expect_ack=True)
            
            if success:
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
                print(f"[ActiveState] Send failed ({self._consecutive_failures}/{self._max_failures})")
            
            # Listen for incoming messages/commands
            timeout = context.config.get('device.listen_timeout', 5000)
            message = context.listen_for_messages(timeout_ms=timeout)
            
            if message:
                context._handle_incoming_message(message)
            
            # Check for too many failures
            if self._consecutive_failures >= self._max_failures:
                print("[ActiveState] ✗ Too many consecutive failures")
                context.set_state(ErrorState(
                    error=f"{self._max_failures} consecutive send failures",
                    origin="ACTIVE"
                ))
                return
            
            # Transition to sleep to save power
            context.set_state(SleepState())
        
        except Exception as e:
            print(f"[ActiveState] ✗ Error: {e}")
            self._consecutive_failures += 1
            
            if self._consecutive_failures >= self._max_failures:
                context.set_state(ErrorState(error=e, origin="ACTIVE"))
            else:
                # Stay in active, retry next cycle
                context.set_state(SleepState())


class SleepState(DeviceState):
    """
    Sleep state: conserve power between reading cycles.
    Uses light sleep or deep sleep depending on config.
    Transition → ActiveState (after sleep interval)
    """
    
    name = "SLEEP"
    
    def handle(self, context):
        interval = context.config.get('device.send_interval', 60)
        sleep_interval = context.config.get('power.sleep_interval', interval)
        
        print(f"[SleepState] Sleeping {sleep_interval}s...")
        
        try:
            # Use machine.lightsleep if available (saves more power)
            try:
                from machine import lightsleep
                lightsleep(sleep_interval * 1000)
            except ImportError:
                # Fallback to regular sleep
                time.sleep(sleep_interval)
        
        except Exception as e:
            print(f"[SleepState] Sleep interrupted: {e}")
        
        # Wake up → back to active
        context.set_state(ActiveState())


class ErrorState(DeviceState):
    """
    Error state: attempt recovery.
    Transition → BootState (on reset attempt)
    Transition → ActiveState (if recovery succeeds)
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
        
        # Publish error event
        context.event_bus.publish('device.error', {
            'error': str(self.error),
            'origin': self.origin,
            'attempt': self._recovery_attempts
        })
    
    def handle(self, context):
        self._recovery_attempts += 1
        
        print(f"[ErrorState] Recovery attempt {self._recovery_attempts}/{self._max_recovery}...")
        
        if self._recovery_attempts > self._max_recovery:
            print("[ErrorState] ✗ Max recovery attempts reached, rebooting...")
            self._reboot(context)
            return
        
        # Wait before retrying (exponential backoff)
        wait_time = min(2 ** self._recovery_attempts, 30)
        print(f"[ErrorState] Waiting {wait_time}s before retry...")
        time.sleep(wait_time)
        
        try:
            if self.origin == "BOOT":
                # Full reboot
                context.set_state(BootState())
            
            elif self.origin == "PAIRING":
                # Retry pairing
                context.set_state(PairingState())
            
            elif self.origin == "ACTIVE":
                # Try returning to active
                context.set_state(ActiveState())
            
            else:
                # Default: full reboot
                context.set_state(BootState())
        
        except Exception as e:
            print(f"[ErrorState] ✗ Recovery failed: {e}")
            # Stay in ErrorState, will retry on next handle()
    
    def _reboot(self, context):
        """Attempt hardware reboot"""
        print("[ErrorState] Rebooting device...")
        try:
            from machine import reset
            reset()
        except ImportError:
            print("[ErrorState] machine.reset() not available, restarting from BootState")
            self._recovery_attempts = 0
            context.set_state(BootState())
