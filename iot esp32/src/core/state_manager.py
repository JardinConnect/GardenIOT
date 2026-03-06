"""
State Manager - Manages device states and transitions.
Works with the DeviceManager façade.
"""

from core.states import BootState, PairingState, ActiveState, SleepState, ErrorState


class StateManager:
    """
    Manages the state machine for the device.
    Encapsulates state transitions and provides clean interface to DeviceManager.
    """

    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.current_state = None

    def set_state(self, new_state):
        """Transition to a new state."""
        if self.current_state:
            self.current_state.exit(self.device_manager)

        old_name = self.current_state.name if self.current_state else "NONE"
        self.current_state = new_state
        self.current_state.enter(self.device_manager)

        print(f"[StateManager] State: {old_name} {self.current_state.name}")

    def handle(self):
        """Handle the current state."""
        if self.current_state:
            self.current_state.handle(self.device_manager)
        else:
            print("[StateManager] No state set")

    def get_current_state(self):
        """Get current state name."""
        return self.current_state.name if self.current_state else "NONE"

    def is_in_state(self, state_name):
        """Check if device is in a specific state."""
        return self.get_current_state() == state_name
