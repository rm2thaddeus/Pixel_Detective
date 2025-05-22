import streamlit as st
import os

# Existing code...

new_folder = st.sidebar.text_input("📁 New folder to merge", value="", key="new_folder").strip().strip('"')
if new_folder:
    if st.sidebar.button("🔀 Merge New Folder"):
        if os.path.exists(new_folder):
            merge_placeholder = st.sidebar.empty()
            merge_progress = st.sidebar.progress(0)
            merge_message = st.sidebar.empty()

            import random
            merge_messages = [
                "🧩 Putting the pieces together…",
                "🔄 Mixing and matching images…",
                "🌪️ Creating a perfect storm of data…",
                "🧙‍♂️ Performing AI magic…",
                "🧬 Splicing image DNA…",
                "🍳 Cooking up a database fusion…",
                "🚢 Merging the flotillas…",
                "🧠 Teaching the AI new tricks…"
            ]
            merge_message.info(random.choice(merge_messages))

            new_images = db_manager.get_image_list(new_folder)
            if new_images:
                # Build a combined list of old+new images
                existing = db_manager.get_image_list(current_folder)
                all_imgs = sorted(set(existing + new_images))
                total = len(all_imgs)
                st.session_state.total_images = total
                st.session_state.current_image_index = 0

                # Spawn a background thread to refresh progress bar
                import threading, time
                def _upd():
                    while st.session_state.get('current_image_index', 0) < total:
                        pct = int((st.session_state['current_image_index']/total) * 100)
                        merge_progress.progress(pct)
                        time.sleep(0.5)
                thread = threading.Thread(target=_upd)
                thread.start()

                # Actually rebuild the DB with all images
                try:
                    success = db_manager.build_database(current_folder, all_imgs)
                    st.session_state.building_database = False
                    thread.join()
                    if success:
                        merge_progress.progress(100)
                        merge_placeholder.success(f"✅ Merged {len(new_images)} new images!")
                        merge_message.success("Database updated and ready to search! 🎉")
                    else:
                        merge_placeholder.error("❌ Merge failed.")
                except Exception as e:
                    st.session_state.building_database = False
                    thread.join()
                    merge_placeholder.error(f"Error merging: {e}")
                    logger.error(f"Error merging folders: {e}")
            else:
                merge_placeholder.warning("No new images found to merge.")
        else:
            st.sidebar.error("New folder does not exist!")

# Show model information at the bottom of sidebar
model_mgr = st.session_state.get('model_manager')
if model_mgr and getattr(model_mgr, 'clip_model', None) is not None:
    st.sidebar.success("✅ CLIP model is loaded and ready")
    device = model_mgr.device
    st.sidebar.info(f"Model is running on: {'GPU' if device.type=='cuda' else 'CPU'}")
else:
    st.sidebar.warning("CLIP model not loaded yet")

# Enable incremental indexing
watch_enabled = st.sidebar.checkbox("📡 Enable Incremental Indexing", value=False, key="enable_watch")

# Existing code... 