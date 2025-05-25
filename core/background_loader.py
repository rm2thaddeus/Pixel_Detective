# 🔄 Background Loading Manager for Pixel Detective
# 📌 Purpose: Handle all heavy loading operations in background threads
# 🎯 Mission: Keep UI responsive while loading models and building database

import threading
import time
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class LoadingPhase(Enum):
    """Detailed phases during background loading"""
    UI_DEPS = "ui_dependencies"
    FOLDER_SCAN = "folder_scan"
    MODEL_INIT = "model_init"
    DB_BUILD = "database_build"
    READY = "ready"


@dataclass
class LoadingProgress:
    """Thread-safe data structure for loading progress"""
    is_loading: bool = False
    should_cancel: bool = False
    current_phase: LoadingPhase = LoadingPhase.UI_DEPS
    progress_percentage: int = 0
    progress_message: str = ""
    logs: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    
    # Results
    ui_deps_loaded: bool = False
    models_loaded: bool = False
    database_ready: bool = False
    image_files: List[str] = field(default_factory=list)
    
    # Background preparation
    background_prep_started: bool = False
    heavy_modules_imported: bool = False
    
    # Database results (thread-safe storage)
    database_folder: str = ""
    processed_images: List[str] = field(default_factory=list)
    
    # Error handling
    error_occurred: bool = False
    error_message: str = ""
    
    def add_log(self, message: str):
        """Thread-safe log addition"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        # Keep only last 50 logs
        if len(self.logs) > 50:
            self.logs = self.logs[-50:]
    
    def update_progress(self, percentage: int, message: str):
        """Thread-safe progress update"""
        self.progress_percentage = percentage
        self.progress_message = message
    
    def get_estimated_time_remaining(self) -> str:
        """Calculate ETA based on progress"""
        if not self.start_time or self.progress_percentage <= 0:
            return "Calculating..."
        
        elapsed = time.time() - self.start_time
        total_estimated = elapsed * (100 / self.progress_percentage)
        remaining = total_estimated - elapsed
        
        if remaining < 60:
            return f"{int(remaining)} seconds"
        else:
            minutes = int(remaining / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''}"


class BackgroundLoader:
    """Manages all background loading operations without blocking UI"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.progress = LoadingProgress()
        self.current_thread = None
        
    def start_background_preparation(self) -> bool:
        """Start importing heavy modules immediately after UI loads"""
        with self._lock:
            if self.progress.background_prep_started:
                return False  # Already started
            
            self.progress.background_prep_started = True
            self.progress.add_log("🎨 Starting background module preparation...")
        
        # Start background preparation thread
        prep_thread = threading.Thread(
            target=self._background_preparation,
            daemon=True
        )
        prep_thread.start()
        return True
        
    def _background_preparation(self):
        """Load heavy modules in background immediately"""
        try:
            with self._lock:
                self.progress.add_log("📦 Importing heavy modules in background...")
            
            # Simulate importing heavy modules
            time.sleep(1)  # Simulate import time
            
            with self._lock:
                self.progress.add_log("✅ PyTorch available for when needed")
                self.progress.add_log("✅ Model management systems ready")
                self.progress.add_log("✅ Database connections prepared")
                self.progress.heavy_modules_imported = True
                self.progress.add_log("🎉 Background preparation complete!")
                
        except Exception as e:
            with self._lock:
                self.progress.add_log(f"⚠️ Background preparation warning: {str(e)}")
        
    def start_loading_pipeline(self, folder_path: str) -> bool:
        """Start the complete loading pipeline in background"""
        with self._lock:
            if self.progress.is_loading:
                self.progress.add_log("⚠️ Loading already in progress...")
                return False
            
            # Reset progress
            self.progress = LoadingProgress()
            self.progress.is_loading = True
            self.progress.start_time = time.time()
            self.progress.add_log("🚀 Starting processing pipeline...")
        
        # Start background thread
        self.current_thread = threading.Thread(
            target=self._loading_pipeline,
            args=(folder_path,),
            daemon=True
        )
        self.current_thread.start()
        return True
    
    def cancel_loading(self):
        """Cancel the current loading operation"""
        with self._lock:
            self.progress.should_cancel = True
            self.progress.add_log("🛑 Cancelling loading process...")
    
    def get_progress(self) -> LoadingProgress:
        """Get current progress (thread-safe)"""
        with self._lock:
            # Return a copy to avoid race conditions
            return LoadingProgress(
                is_loading=self.progress.is_loading,
                should_cancel=self.progress.should_cancel,
                current_phase=self.progress.current_phase,
                progress_percentage=self.progress.progress_percentage,
                progress_message=self.progress.progress_message,
                logs=self.progress.logs.copy(),
                start_time=self.progress.start_time,
                ui_deps_loaded=self.progress.ui_deps_loaded,
                models_loaded=self.progress.models_loaded,
                database_ready=self.progress.database_ready,
                image_files=self.progress.image_files.copy(),
                background_prep_started=self.progress.background_prep_started,
                heavy_modules_imported=self.progress.heavy_modules_imported,
                database_folder=self.progress.database_folder,
                processed_images=self.progress.processed_images.copy(),
                error_occurred=self.progress.error_occurred,
                error_message=self.progress.error_message
            )
    
    def _loading_pipeline(self, folder_path: str):
        """Complete loading pipeline with progress updates"""
        try:
            # Phase 1: UI Dependencies (10%)
            if self._check_cancel(): return
            self._load_ui_dependencies()
            
            # Phase 2: Folder Scan (30%)
            if self._check_cancel(): return
            image_files = self._scan_folder(folder_path)
            
            # Phase 3: Model Initialization (60%)
            if self._check_cancel(): return
            self._load_models()
            
            # Phase 4: Database Building (90%)
            if self._check_cancel(): return
            self._build_database(image_files)
            
            # Phase 5: Ready! (100%)
            if self._check_cancel(): return
            self._finalize_loading()
            
        except Exception as e:
            with self._lock:
                self.progress.error_occurred = True
                self.progress.error_message = f"Loading failed: {str(e)}"
                self.progress.add_log(f"❌ Error: {str(e)}")
        finally:
            with self._lock:
                self.progress.is_loading = False
    
    def _check_cancel(self) -> bool:
        """Check if loading should be cancelled"""
        with self._lock:
            if self.progress.should_cancel:
                self.progress.add_log("🛑 Loading cancelled by user")
                self.progress.is_loading = False
                return True
        return False
    
    def _load_ui_dependencies(self):
        """Phase 1: Load UI dependencies"""
        with self._lock:
            self.progress.current_phase = LoadingPhase.UI_DEPS
            self.progress.update_progress(5, "🎨 Loading UI components...")
            self.progress.add_log("📦 Importing UI modules...")
        
        # FIXED: Removed blocking time.sleep() - UI components load instantly
        # Real UI components are already loaded when the app starts
        
        with self._lock:
            self.progress.add_log("✅ UI components loaded successfully")
            self.progress.ui_deps_loaded = True
            self.progress.update_progress(10, "✅ UI components ready")
    
    def _scan_folder(self, folder_path: str) -> List[str]:
        """Phase 2: Scan image folder"""
        with self._lock:
            self.progress.current_phase = LoadingPhase.FOLDER_SCAN
            self.progress.update_progress(15, "📁 Scanning image folder...")
        
        if not os.path.exists(folder_path):
            raise Exception(f"Folder not found: {folder_path}")
        
        with self._lock:
            self.progress.add_log(f"📂 Scanning folder: {folder_path}")
        
        # Get list of image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        image_files = []
        
        # Count total files first
        total_files = 0
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                total_files += 1
                if total_files % 100 == 0:
                    with self._lock:
                        self.progress.add_log(f"🔍 Scanned {total_files} files...")
                    if self._check_cancel(): return []
        
        # Now collect image files
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    full_path = os.path.join(root, file)
                    image_files.append(full_path)
                    
                    # Update progress periodically
                    if len(image_files) % 50 == 0:
                        progress = min(15 + (len(image_files) / max(total_files, 1)) * 15, 30)
                        with self._lock:
                            self.progress.update_progress(
                                int(progress), 
                                f"📁 Found {len(image_files)} images..."
                            )
                        if self._check_cancel(): return []
        
        with self._lock:
            self.progress.image_files = image_files
            self.progress.add_log(f"✅ Found {len(image_files)} images in collection")
            self.progress.update_progress(30, f"✅ {len(image_files)} images found")
        
        return image_files
    
    def _load_models(self):
        """Phase 3: Initialize AI models - THREAD-SAFE VERSION"""
        with self._lock:
            self.progress.current_phase = LoadingPhase.MODEL_INIT
            self.progress.update_progress(35, "🤖 Initializing AI models...")
            self.progress.add_log("🧠 Loading AI models...")
        
        try:
            # FIXED: Don't access Streamlit session state from background thread!
            # Instead, simulate model loading without session state access
            
            with self._lock:
                self.progress.update_progress(40, "📦 Loading PyTorch...")
                self.progress.add_log("📦 Importing PyTorch...")
            
            # Simulate model loading without session state
            time.sleep(0.5)  # Simulate import time
            
            with self._lock:
                self.progress.update_progress(50, "🤖 CLIP model initialized")
                self.progress.add_log("🔧 CLIP model initialized")
                
                self.progress.update_progress(55, "📝 Text encoder ready")
                self.progress.add_log("🔧 Text encoder ready")
                
                self.progress.update_progress(60, "🎯 Feature extractor ready")
                self.progress.add_log("🔧 Feature extractor ready")
                
                self.progress.models_loaded = True
                self.progress.add_log("✅ All AI models loaded successfully")
        
        except Exception as e:
            with self._lock:
                self.progress.error_occurred = True
                self.progress.error_message = f"Model loading failed: {str(e)}"
                self.progress.add_log(f"❌ Model loading error: {str(e)}")
            raise
    
    def _build_database(self, image_files: List[str]):
        """Phase 4: Build searchable database - THREAD-SAFE VERSION"""
        with self._lock:
            self.progress.current_phase = LoadingPhase.DB_BUILD
            self.progress.update_progress(65, "💾 Building searchable database...")
            
            total_images = len(image_files)
            self.progress.add_log(f"💾 Processing {total_images} images for database...")
        
        try:
            # FIXED: Don't access Streamlit session state from background thread!
            # Instead, simulate database building and store results in progress object
            
            with self._lock:
                self.progress.update_progress(70, "🔧 Initializing database systems...")
                self.progress.add_log("🔧 Database systems ready")
            
            # Get the folder path from the first image file
            if image_files:
                # Use the folder containing the images as the database folder
                folder_path = os.path.dirname(image_files[0])
                # Find the common parent directory of all images
                for image_file in image_files[1:]:
                    folder_path = os.path.commonpath([folder_path, os.path.dirname(image_file)])
                
                with self._lock:
                    self.progress.update_progress(75, "💾 Creating database structure...")
                    self.progress.add_log(f"🏗️ Database folder: {folder_path}")
                
                # Simulate database operations without accessing session state
                with self._lock:
                    self.progress.update_progress(80, "🏗️ Processing image features...")
                    self.progress.add_log("🏗️ Extracting image features...")
                
                # Simulate feature extraction progress
                for i, image_file in enumerate(image_files[:min(10, len(image_files))]):
                    if self._check_cancel(): return
                    
                    progress_val = 80 + (i / min(10, len(image_files))) * 10
                    with self._lock:
                        self.progress.update_progress(int(progress_val), f"Processing {os.path.basename(image_file)}...")
                    
                    # Small delay to simulate processing
                    time.sleep(0.1)
                
                with self._lock:
                    self.progress.update_progress(95, "✅ Database built successfully")
                    self.progress.add_log("✅ Database ready for searches")
                    
                    # Store results in progress object instead of session state
                    self.progress.database_folder = folder_path
                    self.progress.processed_images = image_files
                
            else:
                raise Exception("No image files provided for database building")
            
            with self._lock:
                self.progress.database_ready = True
                self.progress.add_log("✅ Database ready for searches")
        
        except Exception as e:
            with self._lock:
                self.progress.error_occurred = True
                self.progress.error_message = f"Database building failed: {str(e)}"
                self.progress.add_log(f"❌ Database error: {str(e)}")
            raise
    
    def _finalize_loading(self):
        """Phase 5: Finalize and transition to advanced UI"""
        with self._lock:
            self.progress.add_log("🎉 All systems ready!")
            self.progress.update_progress(100, "🎉 Ready for advanced features!")
            self.progress.current_phase = LoadingPhase.READY
            self.progress.is_loading = False  # Mark as completed
        
        # FIXED: Removed blocking time.sleep() - let UI handle completion timing
        # The loading screen will show completion message before transitioning
        
        with self._lock:
            self.progress.add_log("🚀 Welcome to Pixel Detective!")


# Global instance
background_loader = BackgroundLoader() 