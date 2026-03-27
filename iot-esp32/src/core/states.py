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
    
    Flow:
    1. LED on to indicate pairing mode
    2. Listen for LoRa message type P from Pi5
    3. Pi5 sends: B|PA|timestamp|pi5_uid|new_uid;parent_id|E
    4. Save uid and parent_id to config
    5. LED off, transition to ActiveState
    """
    
    name = "PAIRING"
    
    def enter(self, context):
        super().enter(context)
        # Turn on LED to indicate pairing mode
        if hasattr(context.hardware, 'btn_led'):
            context.hardware.btn_led.value(1)
    
    def exit(self, context):
        # Turn off LED
        if hasattr(context.hardware, 'btn_led'):
            context.hardware.btn_led.value(0)
        # Clear any button IRQ events accumulated during pairing
        context._pairing_requested = False
    
    def handle(self, context):
        pairing_config = context.config.get('pairing', {})
        timeout_ms = pairing_config.get('timeout_ms', 5000)
        max_attempts = 10
        
        print(f"[PairingState] Waiting for gateway pairing (timeout={timeout_ms}ms per attempt)")
        
        for attempt in range(1, max_attempts + 1):
            print(f"[PairingState] Listening... ({attempt}/{max_attempts})")
            
            response = context.communication.receive(timeout_ms=timeout_ms)
            
            if response and response.get('type') == 'PA':
                parent_id = response.get('uid', '')
                
                if parent_id:
                    # Save parent_id to config (uid is already set from machine.unique_id)
                    context.config.set('device.parent_id', parent_id)
                    context.config.save()
                    
                    # Send PA_ACK to Pi5
                    context.communication._send_ack('OK', 'PA_ACK')
                    
                    print(f"[PairingState] Paired! uid={context.uid}, parent={parent_id}")
                    context.set_state(ActiveState())
                    return
                else:
                    print(f"[PairingState] Invalid pairing data: no parent_id")
            
            time.sleep(1)
        
        print("[PairingState] Pairing failed after all attempts")
        context.set_state(ErrorState(error="Pairing timeout", origin="PAIRING"))


class ActiveState(DeviceState):
    """
    Active state: delegates to DeviceManager.run_cycle().
    Seul responsable de la transition vers SleepState.
    """
    
    name = "ACTIVE"
    
    def __init__(self):
        self._consecutive_failures = 0
        self._max_failures = 3
        self._had_comm_failure = False

    def enter(self, context):
        super().enter(context)
        context.event_bus.subscribe('communication.send_failed', self._on_send_failed)

    def exit(self, context):
        context.event_bus.unsubscribe('communication.send_failed', self._on_send_failed)

    def _on_send_failed(self, payload):
        self._consecutive_failures += 1
        self._had_comm_failure = True
        print(f"[ActiveState] Comm failure counted ({self._consecutive_failures}/{self._max_failures})")
    
    def handle(self, context):
        print("[ActiveState] Running cycle...")
        self._had_comm_failure = False

        try:
            context.run_cycle()
            if not self._had_comm_failure:
                self._consecutive_failures = 0
        except Exception as e:
            print(f"[ActiveState] Error: {e}")
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_failures:
                print(f"[ActiveState] Too many failures ({self._consecutive_failures}), entering error")
                context.set_state(ErrorState(error=e, origin="ACTIVE"))
                return

        context.set_state(SleepState())


class SleepState(DeviceState):
    """
    Sleep state: conserve power between reading cycles.
    Uses micro-sleep + listen window so the gateway can wake the device via LoRa.
    """
    
    name = "SLEEP"
    
    def exit(self, context):
        # lightsleep wakeup can trigger spurious button IRQs - discard them
        context._pairing_requested = False

    def handle(self, context):
        interval = context.config.get('power.sleep_interval', 15)
        micro_sleep_ms = context.config.get('power.micro_sleep_ms', 1000)
        listen_timeout_ms = context.config.get('power.listen_timeout_ms', 100)
        cycles = (interval * 1000) // micro_sleep_ms
        
        print(f"[SleepState] Sleeping {interval}s ({cycles} cycles with listen window)")
        
        for _ in range(cycles):
            # 1. Micro-sleep
            try:
                from machine import lightsleep
                lightsleep(micro_sleep_ms)
            except ImportError:
                time.sleep_ms(micro_sleep_ms)
            
            # 2. Écoute LoRa rapide - wake sur n'importe quel message entrant
            try:
                msg = context.communication.receive(timeout_ms=listen_timeout_ms)
                if msg:
                    print(f"[SleepState] LoRa message received (type={msg.get('type')}), waking up")
                    context._wake_message = msg
                    context.set_state(ActiveState())
                    return
            except Exception:
                pass
        
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