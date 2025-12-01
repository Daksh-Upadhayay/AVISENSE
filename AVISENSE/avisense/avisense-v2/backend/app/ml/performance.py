"""
Performance optimization utilities for model inference.
"""

import torch
import asyncio
from typing import List, Dict, Any
from collections import deque
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BatchPredictor:
    """
    Batches multiple prediction requests together for improved throughput.
    """
    
    def __init__(self, max_batch_size: int = 32, max_wait_ms: int = 100):
        """
        Initialize batch predictor.
        
        Args:
            max_batch_size: Maximum number of requests to batch together
            max_wait_ms: Maximum time to wait for batch to fill (milliseconds)
        """
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms / 1000.0  # Convert to seconds
        self.queue = deque()
        self.processing = False
        
    async def predict(self, model_fn, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add prediction request to batch queue.
        
        Args:
            model_fn: Async function that performs the actual prediction
            input_data: Input data for prediction
            
        Returns:
            Prediction result
        """
        # Create a future for this request
        future = asyncio.Future()
        request = {
            'input_data': input_data,
            'future': future,
            'timestamp': datetime.now()
        }
        
        self.queue.append(request)
        
        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self._process_batch(model_fn))
        
        # Wait for result
        return await future
    
    async def _process_batch(self, model_fn):
        """Process queued requests in batches."""
        self.processing = True
        
        try:
            while self.queue:
                # Wait for batch to fill or timeout
                start_time = datetime.now()
                while len(self.queue) < self.max_batch_size:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= self.max_wait_ms:
                        break
                    await asyncio.sleep(0.001)  # 1ms sleep
                
                # Collect batch
                batch = []
                batch_size = min(len(self.queue), self.max_batch_size)
                
                for _ in range(batch_size):
                    if self.queue:
                        batch.append(self.queue.popleft())
                
                if not batch:
                    break
                
                # Process batch
                try:
                    # Run predictions concurrently
                    tasks = [model_fn(req['input_data']) for req in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Set results
                    for req, result in zip(batch, results):
                        if isinstance(result, Exception):
                            req['future'].set_exception(result)
                        else:
                            req['future'].set_result(result)
                    
                    logger.info(f"Processed batch of {len(batch)} predictions")
                    
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    # Set exception for all requests in batch
                    for req in batch:
                        if not req['future'].done():
                            req['future'].set_exception(e)
        
        finally:
            self.processing = False


class GPUManager:
    """
    Manages GPU device selection and memory.
    """
    
    @staticmethod
    def get_device(prefer_gpu: bool = True) -> str:
        """
        Get the best available device.
        
        Args:
            prefer_gpu: Whether to prefer GPU if available
            
        Returns:
            Device string ('cuda' or 'cpu')
        """
        if prefer_gpu and torch.cuda.is_available():
            device = 'cuda'
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        else:
            device = 'cpu'
            logger.info("Using CPU for inference")
        
        return device
    
    @staticmethod
    def optimize_for_inference(model: torch.nn.Module) -> torch.nn.Module:
        """
        Optimize model for inference.
        
        Args:
            model: PyTorch model
            
        Returns:
            Optimized model
        """
        model.eval()
        
        # Disable gradient computation
        for param in model.parameters():
            param.requires_grad = False
        
        # Use inference mode
        torch.set_grad_enabled(False)
        
        # Enable cuDNN auto-tuner for faster inference
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
        
        logger.info("Model optimized for inference")
        
        return model
    
    @staticmethod
    def clear_cache():
        """Clear GPU cache to free memory."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")


class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance.
    
    Prevents cascading failures by temporarily disabling failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_attempts: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before attempting recovery
            half_open_attempts: Number of test requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_attempts = half_open_attempts
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open
        self.half_open_count = 0
    
    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if circuit is open
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half_open'
                self.half_open_count = 0
                logger.info("Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            # Call function
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == 'half_open':
                self.half_open_count += 1
                if self.half_open_count >= self.half_open_attempts:
                    self._reset()
                    logger.info("Circuit breaker CLOSED - service recovered")
            elif self.state == 'closed':
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self._record_failure()
            raise e
    
    def _record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == 'half_open':
            # Failure in half-open state - reopen circuit
            self.state = 'open'
            logger.warning("Circuit breaker OPEN - service still failing")
        elif self.failure_count >= self.failure_threshold:
            # Too many failures - open circuit
            self.state = 'open'
            logger.error(f"Circuit breaker OPEN - {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout_seconds
    
    def _reset(self):
        """Reset circuit breaker to closed state."""
        self.state = 'closed'
        self.failure_count = 0
        self.half_open_count = 0
        self.last_failure_time = None
