"""
Purpose: Checks CUDA availability and prints relevant GPU details.
Latest Changes: Created a diagnostic tool for CUDA detection for troubleshooting.
Key Logic: Uses torch.cuda.is_available(), torch.cuda.device_count(), and torch.cuda.get_device_name to display CUDA-related info.
File Path: diagnose_cuda.py
Reasoning: Diagnosing CUDA availability will help clarify if the error is due to environmental setup or code integration with torch.
"""

import torch

def check_cuda():
    cuda_available = torch.cuda.is_available()
    print("CUDA Available:", cuda_available)
    if cuda_available:
        device_count = torch.cuda.device_count()
        print("CUDA Device Count:", device_count)
        for i in range(device_count):
            print(f"CUDA Device {i}: {torch.cuda.get_device_name(i)}")
    else:
        print("CUDA is not available. Please check your GPU driver and PyTorch installation.")

if __name__ == "__main__":
    check_cuda() 