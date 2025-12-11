#!/usr/bin/env python3
"""
System test script - validates video detection and basic functionality
"""
import os
from pathlib import Path
from config import Config
from voting import VotingSession

def test_video_detection():
    """Test if videos are detected correctly"""
    print("=== VIDEO DETECTION TEST ===")
    video_dir = Path(Config.VIDEOS_FOLDER)

    if not video_dir.exists():
        print(f"❌ Video directory does not exist: {video_dir}")
        return False

    videos = list(video_dir.glob("*.mp4"))
    print(f"Found {len(videos)} videos:")
    for v in videos:
        size_mb = v.stat().st_size / (1024 * 1024)
        print(f"  - {v.name} ({size_mb:.2f} MB)")

    if len(videos) == 0:
        print("❌ No videos found!")
        return False

    print(f"✅ Video detection working ({len(videos)} videos)")
    return True

def test_voting_system():
    """Test voting mechanics"""
    print("\n=== VOTING SYSTEM TEST ===")
    import time

    session = VotingSession()

    # Start a voting session with mock options
    session.start([
        ("A", Path("videos/test_A.mp4")),
        ("B", Path("videos/test_B.mp4")),
        ("C", Path("videos/test_C.mp4"))
    ])

    # Simulate votes
    now = time.time()
    session.record_vote("twitch", "user1", "A", now)
    session.record_vote("twitch", "user2", "B", now + 0.1)
    session.record_vote("kick", "user3", "A", now + 0.2)
    session.record_vote("kick", "user4", "B", now + 0.3)
    session.record_vote("twitch", "user5", "A", now + 0.4)  # A should win (3 votes)

    results = session.get_results()
    winner = session.get_winner()

    print(f"Vote counts: {results}")
    print(f"Total voters: {session.total_votes}")
    if winner:
        print(f"Winner: {winner[0]} ({winner[1].name})")
    else:
        print("Winner: None")

    if winner and winner[0] == "A":
        print("✅ Voting system working correctly")
        return True
    else:
        print(f"❌ Expected winner 'A', got '{winner[0] if winner else None}'")
        return False

def test_config():
    """Test configuration loading"""
    print("\n=== CONFIGURATION TEST ===")

    required_vars = [
        ("TWITCH_STREAM_KEY", Config.TWITCH_STREAM_KEY),
        ("KICK_STREAM_KEY", Config.KICK_STREAM_KEY),
        ("TWITCH_CHANNEL", Config.TWITCH_CHANNEL),
        ("KICK_CHANNEL", Config.KICK_CHANNEL),
    ]

    all_ok = True
    for name, value in required_vars:
        if value and value != "xxxxx" and value != "your_":
            print(f"  ✅ {name}: {value[:20]}..." if len(value) > 20 else f"  ✅ {name}: {value}")
        else:
            print(f"  ❌ {name}: NOT SET")
            all_ok = False

    print(f"Stream resolution: {Config.STREAM_RESOLUTION}")
    print(f"Stream FPS: {Config.STREAM_FPS}")
    print(f"Stream bitrate: {Config.STREAM_BITRATE}")

    if all_ok:
        print("✅ Configuration loaded correctly")
    else:
        print("⚠️  Some configuration missing (expected in restricted environment)")

    return all_ok

def test_ffmpeg():
    """Test FFmpeg availability"""
    print("\n=== FFMPEG TEST ===")
    result = os.system("ffmpeg -version > /dev/null 2>&1")
    if result == 0:
        print("✅ FFmpeg is available")
        # Get version
        import subprocess
        version = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        print(f"  {version.stdout.split(chr(10))[0]}")
        return True
    else:
        print("❌ FFmpeg not found")
        return False

if __name__ == "__main__":
    print("Watts-A System Test Suite\n")

    results = []
    results.append(("FFmpeg", test_ffmpeg()))
    results.append(("Video Detection", test_video_detection()))
    results.append(("Voting System", test_voting_system()))
    results.append(("Configuration", test_config()))

    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🚀 System ready for launch!")
    else:
        print("\n⚠️  Some tests failed - review above")
