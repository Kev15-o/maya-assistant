# Streamlit Deployment Guide

## Local Testing

To run the Streamlit app locally:

```bash
streamlit run streamlit_app.py
```

The app will automatically:
1. Start the voice assistant on a background thread
2. Start the state API server on port 5051
3. Display the animated M.A.Y.A face in the browser on port 8501

Visit `http://localhost:8501` in your browser.

## Deploying to Streamlit Cloud

### Prerequisites
- GitHub repository with the code
- Streamlit Cloud account (https://streamlit.io/cloud)

### Steps

1. **Push code to GitHub:**
   ```bash
   git add -A
   git commit -m "Add Streamlit deployment configuration"
   git push origin main
   ```

2. **Connect to Streamlit Cloud:**
   - Go to https://share.streamlit.io/
   - Click "New app"
   - Connect your GitHub repository
   - Select this repo and choose `streamlit_app.py` as the main file

3. **Configuration:**
   - Streamlit Cloud will automatically read `.streamlit/config.toml`
   - The app will run in headless mode with proper CORS settings

## Environment Setup

Make sure `requirements.txt` includes all dependencies:
- `flask` - For the state API server
- `SpeechRecognition` - For voice input
- `edge-tts` - For voice generation
- `pygame` - **Critical for audio playback** (enables full voice functionality)
- `requests`, `wikipedia`, `pyjokes` - For assistant features
- `streamlit` - The web framework

## Troubleshooting

### "Preview Mode" Error
If the assistant runs in preview/limited mode without voice:
- **Solution:** Make sure `pygame` is installed and listed in `requirements.txt`
- pygame is required for actual audio playback; without it, text is only printed

### API Not Connecting
If the embedded face shows errors:
- Check that port 5051 is available
- Verify CORS is enabled in `.streamlit/config.toml`
- The `state_api.py` must be running on a separate port than Streamlit

### Microphone Access Issues
- On Linux in containers: Audio input may require special permissions
- The app attempts to use the system microphone via SpeechRecognition
- In cloud environments without audio hardware, voice input will fail gracefully

## Architecture Notes

This deployment maintains the same architecture as the Flask version:
- **Assistant Thread:** Runs the voice loop independently
- **State API:** Lightweight JSON endpoint on port 5051
- **Streamlit:** Serves the web UI and embeds the HTML face
- **Templates/index.html:** Same animated face markup, reused across all frontends

All three interfaces (Flask, Streamlit, Desktop) share the same `state.py` object and `assistant.py` logic.
