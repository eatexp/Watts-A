# Watts-A - 24/7 Alan Watts Tribute Broadcast Station

A headless streaming service that plays videos to Twitch, Kick, and Rumble simultaneously with interactive chat voting.

## Features

- **Multi-platform streaming** - Twitch, Kick, and Rumble simultaneously via FFmpeg tee muxer
- **Interactive chat voting** - Viewers vote for next video with A/B/C/D in chat
- **Dynamic overlays** - Shows "Now Playing", voting options, countdown, and live vote tallies
- **Auto-recovery** - Supervisor script restarts on crashes, dead man's switch kills frozen streams
- **Safe mode** - Falls back to random selection if voting system fails
- **Content harvester** - Automatically downloads fresh videos from YouTube channels

## Quick Start

### 1. Install Dependencies

```bash
# System packages
apt install -y ffmpeg fonts-dejavu python3 python3-pip git

# Python packages
pip3 install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Copy example config
cp .env.example .env

# Edit with your credentials
nano .env
```

Required settings:
- `TWITCH_STREAM_KEY` - From https://dashboard.twitch.tv/settings/stream
- `KICK_STREAM_KEY` - From https://kick.com/dashboard/settings/stream
- `TWITCH_ACCESS_TOKEN` - From https://twitchtokengenerator.com
- `TWITCH_CHANNEL` - Your Twitch username
- `KICK_CHANNEL` - Your Kick username

### 3. Enable Overlay System

**CRITICAL:** The overlay is currently disabled for testing. Re-enable it:

```bash
# Automated method (recommended)
python3 enable_overlay.py

# OR manual method
# Edit stream_manager.py lines 45-68
# Uncomment the drawtext filter lines
```

### 4. Get Content

```bash
# Download videos from configured YouTube channels
python3 downloader.py

# Wait for at least 10 videos (15+ minutes each)
# Check progress: ls -lh videos/
```

### 5. Validate System

```bash
# Run comprehensive pre-flight checks
python3 preflight_check.py

# Must show: "🚀 ALL SYSTEMS GO!"
```

### 6. Launch Broadcast

```bash
# Start with auto-restart supervisor
./run.sh

# Monitor logs
tail -f watts-a.log
```

## Verification Checklist

Before going live, verify:

- [ ] `python3 preflight_check.py` shows "ALL SYSTEMS GO"
- [ ] At least 10 videos in `videos/` folder
- [ ] No test videos (test_A.mp4, etc.) in library
- [ ] Overlay enabled in stream_manager.py
- [ ] Stream visible at https://twitch.tv/YOUR_CHANNEL
- [ ] Send test vote in Twitch chat (type "A")
- [ ] Overlay shows vote count updating

## Architecture

```
main.py (BroadcastStation)
    ├── stream_manager.py   # FFmpeg tee muxer → 3 RTMP destinations
    ├── chat_listener.py    # Twitch (TwitchIO) + Kick (Pusher WebSocket)
    ├── voting.py           # One-vote-per-user, first-to-reach tie-breaker
    ├── overlay.py          # Dynamic FFmpeg drawtext (reload=1)
    └── config.py           # Environment variables from .env

downloader.py              # Content harvester (yt-dlp)
run.sh                     # Supervisor (auto-restart on crash)
```

## Configuration

### Stream Settings (`.env`)

```bash
STREAM_RESOLUTION=1920x1080  # 1080p recommended
STREAM_FPS=30                # 30 fps standard
STREAM_BITRATE=3000k         # 3000k for 1080p30
```

### Content Harvester (`.env`)

```bash
# Comma-separated YouTube channel URLs
SOURCE_CHANNELS=https://www.youtube.com/@AfterSkool,https://www.youtube.com/@AlanWattsOrg

MAX_VIDEOS=30                # Keep library under 30 videos
MIN_VIDEO_DURATION=900       # 15 minutes minimum
HARVESTER_INTERVAL_HOURS=4   # Check for new content every 4 hours
```

### Voting Settings (`.env`)

```bash
VOTE_WINDOW_SECONDS=60       # Start voting 60s before video ends
VOTE_GRACE_PERIOD_SECONDS=5  # Extra 5s for stream latency
```

## Monitoring

### Check Stream Status

```bash
# Check if streaming
ps aux | grep ffmpeg

# View live logs
tail -f watts-a.log | grep -E "Vote|Winner|ERROR"

# Check current overlay
cat /tmp/watts_overlay.txt
```

### Health Metrics

- **CPU:** 20-30% (single core for x264 encoding)
- **RAM:** 200-300 MB
- **Network:** ~400 KB/s upload (3000k bitrate)
- **Disk:** ~1 GB per video (30 GB for full library)

## Troubleshooting

### Stream Not Starting

```bash
# Check FFmpeg
ffmpeg -version

# Check configuration
python3 -c "from config import Config; Config.validate()"

# Check video library
ls -lh videos/
```

### Overlay Not Showing

```bash
# Verify drawtext filter available
ffmpeg -filters 2>&1 | grep drawtext

# If missing, install full FFmpeg
apt install -y ffmpeg fonts-dejavu

# Re-enable overlay
python3 enable_overlay.py
```

### Kick Chat Not Working

```bash
# Check logs for chatroom ID
tail -f watts-a.log | grep Kick

# If "Failed to fetch Kick chatroom ID", manually set:
# Get ID: curl "https://kick.com/api/v2/channels/YOUR_CHANNEL" | jq '.chatroom.id'
# Add to .env: KICK_CHATROOM_ID=123456
```

### No Votes Being Counted

```bash
# Test Twitch bot connection
tail -f watts-a.log | grep "Twitch bot connected"

# Test Kick listener
tail -f watts-a.log | grep "Kick listener started"

# Send test vote in chat (type "A")
# Should see: [Vote] username (twitch) voted: A
```

## Maintenance

### Daily
- Check logs for errors: `grep ERROR watts-a.log`
- Verify stream is live at stream URL
- Monitor vote participation

### Weekly
- Run `python3 downloader.py` for fresh content
- Review most/least popular videos
- Check disk space: `df -h`

### Monthly
- Rotate stream keys (security best practice)
- Update dependencies: `pip3 install -r requirements.txt --upgrade`
- Clean up old logs: `rm watts-a.log.old`

## Emergency Procedures

### Stop Everything

```bash
pkill -f "python3 main.py"
pkill -f ffmpeg
```

### Restart

```bash
./run.sh
```

### View Recent Errors

```bash
tail -100 watts-a.log | grep ERROR
```

## Files & Directories

```
.
├── main.py                # Main broadcast controller
├── stream_manager.py      # FFmpeg streaming
├── chat_listener.py       # Twitch + Kick chat bots
├── voting.py              # Vote tracking and winner selection
├── overlay.py             # Dynamic overlay system
├── downloader.py          # YouTube content harvester
├── config.py              # Configuration management
├── utils.py               # Helper functions
├── run.sh                 # Supervisor script
├── .env                   # Credentials (create from .env.example)
├── .env.example           # Configuration template
├── requirements.txt       # Python dependencies
├── test_system.py         # System validation tests
├── preflight_check.py     # Pre-launch validation
├── enable_overlay.py      # Overlay re-enable helper
├── PRODUCTION_READINESS.md # Deployment guide
├── CLAUDE.md              # AI assistant instructions
└── videos/                # Video library (auto-created)
```

## Documentation

- **[PRODUCTION_READINESS.md](PRODUCTION_READINESS.md)** - Comprehensive deployment guide, edge cases, troubleshooting
- **[CLAUDE.md](CLAUDE.md)** - Project overview and design patterns for AI assistants

## Security Notes

- Never commit `.env` file (contains stream keys and OAuth tokens)
- Rotate stream keys monthly
- Use read-only chat bot (no moderation commands)
- Monitor logs for unauthorized access attempts

## Performance Tuning

### Low CPU Systems

Edit `stream_manager.py` and change preset:
```python
"-preset", "ultrafast",  # Instead of "veryfast"
```

### High Quality Streams

Edit `.env`:
```bash
STREAM_BITRATE=6000k      # 6 Mbps for crisp 1080p
```

## Credits

Built for the Alan Watts community. Designed to run 24/7 on a VPS without OBS or manual intervention.

## License

See LICENSE file for details.
