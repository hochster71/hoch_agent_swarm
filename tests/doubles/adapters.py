class DummyMockAdapter:
    def build_request(self, run_id, seat, prompt): 
        return {}
        
    def dispatch_mock(self, req): 
        return b'{}'
        
    def resolve_model_identity(self): 
        return "mock_model"
        
    @property
    def parsed_response(self): 
        return {"action": "MOCK"}
