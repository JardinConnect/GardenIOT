class CommunicationProtocol:
    """Interface commune pour tous les protocoles de communication"""

    def __init__(self, name):
        self.name = name
        self._connected = False

    def connect(self):
        """Établir la connexion"""
        raise NotImplementedError

    def disconnect(self):
        """Fermer la connexion"""
        raise NotImplementedError

    def send(self, data):
        """Envoyer des données"""
        raise NotImplementedError

    def receive(self):
        """Recevoir des données"""
        raise NotImplementedError

    def is_connected(self):
        """Vérifier l'état de la connexion"""
        return self._connected