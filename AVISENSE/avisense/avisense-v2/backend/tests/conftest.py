import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment."""
    import os
    os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'test-key'
    os.environ['MODEL_PATH'] = './models'
    
    # Load model before tests
    from app.ml.model_loader import load_model
    import asyncio
    asyncio.run(load_model())
