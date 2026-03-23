class SessionMemory:
    """
    Short-term rolling window memory.
    Stores last N messages for context injection.
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.messages = []

    def add(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content
        })

        if len(self.messages) > self.window_size:
            self.messages = self.messages[-self.window_size:]

    def get_history(self):
        return self.messages

    def clear(self):
        self.messages = []