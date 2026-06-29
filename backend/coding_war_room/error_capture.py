class ErrorCapture:
    def __init__(self):
        self.captured_errors = []
        
    def capture_error(self, error: dict):
        self.captured_errors.append(error)
        
    def get_latest_error(self) -> dict:
        return self.captured_errors[-1] if self.captured_errors else None
