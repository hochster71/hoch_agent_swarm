from unittest.mock import patch, MagicMock
from backend.local_runtime_supervisor import LocalRuntimeSupervisor
from backend.runtime_process import RuntimeProcessState

def test_supervisor_check_once_reachable():
    with patch("backend.local_runtime_supervisor.RuntimeProcessBus") as mock_bus_cls, \
         patch("backend.local_runtime_supervisor.get_providers") as mock_get_providers:
        
        mock_bus = MagicMock()
        mock_bus_cls.return_value = mock_bus
        
        # Return mock local provider config dictionary
        mock_get_providers.return_value = {
            "ollama_test": {
                "type": "local",
                "base_url": "http://localhost:11434",
                "api_style": "ollama",
                "enabled": True
            }
        }
        
        supervisor = LocalRuntimeSupervisor()
        
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            
            results = supervisor.check_once()
            
            assert len(results) == 1
            assert results[0].provider == "ollama_test"
            assert results[0].reachable is True
            assert results[0].error is None
            
            # Verify event emission
            mock_bus.emit.assert_called_once()
            args, kwargs = mock_bus.emit.call_args
            assert args[0].value == "LOCAL_MODEL_HEALTH"
            assert args[1] == RuntimeProcessState.LIVE

def test_supervisor_check_once_unreachable():
    with patch("backend.local_runtime_supervisor.RuntimeProcessBus") as mock_bus_cls, \
         patch("backend.local_runtime_supervisor.get_providers") as mock_get_providers:
        
        mock_bus = MagicMock()
        mock_bus_cls.return_value = mock_bus
        
        mock_get_providers.return_value = {
            "lm_studio_test": {
                "type": "local",
                "base_url": "http://localhost:1234",
                "api_style": "openai",
                "enabled": True
            }
        }
        
        supervisor = LocalRuntimeSupervisor()
        
        with patch("requests.get", side_effect=Exception("Connection refused")):
            results = supervisor.check_once()
            
            assert len(results) == 1
            assert results[0].provider == "lm_studio_test"
            assert results[0].reachable is False
            assert "Connection refused" in results[0].error
            
            # Verify event emission with FAILED state
            mock_bus.emit.assert_called_once()
            args, kwargs = mock_bus.emit.call_args
            assert args[0].value == "LOCAL_MODEL_HEALTH"
            assert args[1] == RuntimeProcessState.FAILED
