#!/usr/bin/env python3
"""
Helper script to re-enable the overlay system in stream_manager.py.

The overlay is disabled by default for testing environments without
full FFmpeg. This script automatically re-enables it for production.
"""
import subprocess
import sys
from pathlib import Path


def check_ffmpeg_drawtext():
    """Check if FFmpeg has drawtext filter."""
    result = subprocess.run(
        ["ffmpeg", "-filters"],
        capture_output=True,
        text=True,
        check=False
    )

    if "drawtext" in result.stdout:
        print("✅ FFmpeg has drawtext filter")
        return True
    else:
        print("❌ FFmpeg does NOT have drawtext filter!")
        print("\n🔧 Install full FFmpeg:")
        print("   apt install -y ffmpeg fonts-dejavu")
        return False


def check_font_exists():
    """Check if the required font file exists."""
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

    if font_path.exists():
        print(f"✅ Font file exists: {font_path}")
        return True
    else:
        print(f"⚠️  Font file not found: {font_path}")
        print("\n🔧 Install fonts:")
        print("   apt install -y fonts-dejavu")
        return False


def enable_overlay():
    """Re-enable overlay in stream_manager.py."""
    stream_manager = Path("stream_manager.py")

    if not stream_manager.exists():
        print(f"❌ {stream_manager} not found!")
        return False

    # Read current content
    content = stream_manager.read_text()

    # Check if already enabled
    if "# OVERLAY DISABLED" not in content:
        print("✅ Overlay already enabled!")
        return True

    print("\n🔧 Enabling overlay in stream_manager.py...")

    # Replace the disabled version with enabled version
    original = '''    # OVERLAY DISABLED: imageio-ffmpeg lacks drawtext filter
    # Build tee output for multiple destinations
    tee_outputs = "|".join(f"[f=flv]{url}" for url in rtmp_urls)

    cmd = [
        "ffmpeg",
        "-re",  # Read input at native frame rate
        "-i", str(video_path),
        # "-vf", drawtext_filter,  # DISABLED: No drawtext support
        "-c:v", "libx264",'''

    replacement = '''    # Build drawtext filter for overlay
    drawtext_filter = (
        f"drawtext="
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"textfile={Config.OVERLAY_FILE}:"
        f"reload=1:"
        f"fontcolor=white:"
        f"fontsize=24:"
        f"box=1:"
        f"boxcolor=black@0.5:"
        f"boxborderw=5:"
        f"x=10:y=10"
    )

    # Build tee output for multiple destinations
    tee_outputs = "|".join(f"[f=flv]{url}" for url in rtmp_urls)

    cmd = [
        "ffmpeg",
        "-re",  # Read input at native frame rate
        "-i", str(video_path),
        "-vf", drawtext_filter,  # Dynamic overlay
        "-c:v", "libx264",'''

    if original in content:
        new_content = content.replace(original, replacement)
        stream_manager.write_text(new_content)
        print("✅ Overlay ENABLED successfully!")
        print(f"\n📝 Modified: {stream_manager}")
        return True
    else:
        print("⚠️  Could not find expected code pattern in stream_manager.py")
        print("   Manual edit may be required")
        return False


def main():
    """Main entry point."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           WATTS-A OVERLAY ENABLE HELPER                      ║
╚══════════════════════════════════════════════════════════════╝
""")

    # Step 1: Check FFmpeg
    print("Step 1: Checking FFmpeg capabilities...")
    if not check_ffmpeg_drawtext():
        print("\n❌ CANNOT ENABLE: FFmpeg lacks drawtext filter")
        print("   Install full FFmpeg first, then run this script again")
        sys.exit(1)

    # Step 2: Check font
    print("\nStep 2: Checking font installation...")
    font_ok = check_font_exists()
    if not font_ok:
        print("   (Overlay will work but may have fallback font issues)")

    # Step 3: Enable overlay
    print("\nStep 3: Enabling overlay in code...")
    if not enable_overlay():
        sys.exit(1)

    # Step 4: Verify
    print("\n" + "="*60)
    print("✅ OVERLAY ENABLED SUCCESSFULLY!")
    print("="*60)
    print("\n📋 Next steps:")
    print("   1. Restart the broadcast: ./run.sh")
    print("   2. Check overlay file: cat /tmp/watts_overlay.txt")
    print("   3. Verify text appears on stream")
    print("\n🎬 Viewers will now see:")
    print("   - Now Playing info")
    print("   - Voting options and countdown")
    print("   - Live vote tallies")
    print("   - Winner announcements")


if __name__ == "__main__":
    main()
