# 📂 File Path: /project_root/utils/cuda_utils.py
# 📌 Purpose: Utility functions for CUDA and GPU memory management.
# 🔄 Latest Changes: Created module with CUDA utility functions.
# ⚙️ Key Logic: Provides functions to check CUDA availability and GPU memory usage.
# 🧠 Reasoning: Centralizes CUDA-related functionality for better code organization.

import torch
import logging

logger = logging.getLogger(__name__)

def check_cuda_availability():
    """
    Checks CUDA availability and provides detailed information.

    Returns:
        tuple: (bool, str) - CUDA availability (True/False) and a message.
    """
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        message = f"CUDA is available! Number of CUDA devices: {device_count}\n"
        for i in range(device_count):
            message += f"  Device {i}: {torch.cuda.get_device_name(i)}\n"
            message += f"    Total Memory: {torch.cuda.get_device_properties(i).total_memory / (1024**3):.2f} GB\n"
        return True, message
    else:
        return False, "CUDA is not available. Check your NVIDIA driver and CUDA installation."

def check_gpu_memory():
    """
    Checks available GPU memory and returns information about current usage.
    
    Returns:
        dict: Information about GPU memory usage
    """
    if not torch.cuda.is_available():
        return {
            "available": False,
            "message": "CUDA is not available"
        }
    
    try:
        # Get total memory
        total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        
        # Get current allocated and reserved memory
        allocated_memory = torch.cuda.memory_allocated(0) / (1024**3)  # GB
        reserved_memory = torch.cuda.memory_reserved(0) / (1024**3)  # GB
        
        # Calculate free memory (this is an approximation)
        free_memory = total_memory - allocated_memory
        
        return {
            "available": True,
            "total_memory_gb": total_memory,
            "allocated_memory_gb": allocated_memory,
            "reserved_memory_gb": reserved_memory,
            "free_memory_gb": free_memory,
            "message": f"GPU Memory: {allocated_memory:.2f}GB used / {total_memory:.2f}GB total"
        }
    except Exception as e:
        logger.error(f"Error checking GPU memory: {e}")
        return {
            "available": False,
            "error": str(e),
            "message": f"Error checking GPU memory: {e}"
        }

def clean_gpu_memory():
    """
    Cleans up GPU memory by emptying cache and collecting garbage.
    """
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    import gc
    gc.collect()

def log_cuda_memory_usage(tag=""):
    """
    Log current CUDA memory usage with an optional tag for identification.
    
    Args:
        tag (str): Optional identifier for the log entry
    """
    if not torch.cuda.is_available():
        return
    
    try:
        # Get memory usage statistics
        allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)  # MB
        reserved = torch.cuda.memory_reserved(0) / (1024 * 1024)  # MB
        max_allocated = torch.cuda.max_memory_allocated(0) / (1024 * 1024)  # MB
        
        # Create log message
        tag_str = f"[{tag}] " if tag else ""
        log_message = f"{tag_str}CUDA Memory - Allocated: {allocated:.2f} MB, Reserved: {reserved:.2f} MB, Peak: {max_allocated:.2f} MB"
        
        # Log the message
        logger.info(log_message)
        
    except Exception as e:
        logger.error(f"Error logging CUDA memory: {e}") 