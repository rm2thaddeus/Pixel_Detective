# CHANGELOG

## [Unreleased]

### Added
- Created this changelog to track environment and documentation changes.
- Full support for DNG (RAW) images: DNG files are now processed for both CLIP embeddings and BLIP captions using rawpy and PIL interoperability.
- Results summary: After each batch run, a summary of all processed images, their captions, and embedding status can be printed and saved to results_summary.txt in the project root by using the --save-summary flag (default: off).

### Changed
- Upgraded to CUDA-enabled PyTorch (torch==2.7.0+cu118, torchvision==0.22.0+cu118, torchaudio==2.7.0+cu118) for GPU acceleration.
- Updated `docs/README.md` with new installation, verification, and troubleshooting instructions for CUDA-enabled PyTorch.
- Updated `docs/current_requirements.txt` to reflect new torch/vision/audio versions and added pip cache troubleshooting note.
- Updated `docs/architecture.md` and `docs/roadmap.md` to reference the new environment setup and GPU troubleshooting.

### Fixed
- Resolved disk space issues by purging pip cache (`pip cache purge`).
- Ensured all scripts and the MVP pipeline now use the GPU if available.

### Notes
- If you see `torch.cuda.is_available() == False`, check your NVIDIA drivers, CUDA toolkit, and ensure you installed the correct PyTorch version for your CUDA version.
- If you run out of disk space during installation, clear your pip cache with `pip cache purge`. 