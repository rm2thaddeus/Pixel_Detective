# 🕵️‍♂️ Pixel Detective

Lightning-fast AI image search with smart 3-screen progressive UX.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

## 🎯 3-Screen UX Flow

### Screen 1: Fast UI (Instant Launch)
- ⚡ **Loads in <1 second**
- 📁 Folder selection interface
- 🎨 Background UI component loading
- 💡 Smart user guidance

### Screen 2: Loading (Engaged Progress)
- 📊 **Real-time progress tracking**
- 🔄 Live logs and phase indicators
- ⏱️ Time estimation and user controls
- 🎯 Excitement building for features

### Screen 3: Advanced UI (Full Features)
- 🔍 **Text and image search**
- 🎮 AI guessing game
- 🌐 Latent space exploration
- 👥 Duplicate detection

## 🧠 Smart Loading Philosophy

- **Load what you need, when you need it**
- **Never block the UI** - everything in background
- **Respect user flow** - clear progression
- **Progressive enhancement** - features unlock naturally

## 🛠️ Architecture

```
app.py (Entry Point)
├── core/
│   ├── app_state.py          # State management
│   ├── background_loader.py  # Background processing
│   └── screen_renderer.py    # Screen routing
└── screens/
    ├── fast_ui_screen.py     # Screen 1: Instant UI
    ├── loading_screen.py     # Screen 2: Progress
    └── advanced_ui_screen.py # Screen 3: Full features
```

## 🎨 Key Features

- **Instant startup** - No waiting for unused features
- **Smart state management** - Clear transitions between screens
- **Contextual sidebars** - Relevant info for each screen
- **Graceful error handling** - Recovery options at every step
- **Progressive disclosure** - Show features when ready

## 🔧 Development

To enable debug mode, uncomment the debug line in `core/screen_renderer.py`:

```python
# ScreenRenderer.show_debug_info()  # Uncomment for debugging
```

## 📊 User Experience Goals

- **Instant Launch**: <1 second to first interaction
- **Engaged Loading**: User stays engaged during processing
- **Smooth Transitions**: No jarring UI changes
- **Clear Progress**: Always know what's happening
- **Recoverable Errors**: Graceful error handling

Built with ❤️ for the perfect user experience. 