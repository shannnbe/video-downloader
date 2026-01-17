import os
import asyncio
import yt_dlp
import requests
import re
from pathlib import Path
from config import DOWNLOADS_DIR, MAX_FILE_SIZE_MB, DOWNLOAD_TIMEOUT

# Create downloads directory if it doesn't exist
Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)


def is_valid_url(text: str) -> bool:
    """Check if the text contains a valid URL."""
    url_patterns = [
        'youtube.com', 'youtu.be',
        'instagram.com',
        'tiktok.com',
        'twitter.com', 'x.com',
        'facebook.com', 'fb.watch',
        'smule.com'
    ]
    
    # Check if any of the patterns are in the text
    return any(pattern in text.lower() for pattern in url_patterns)


def extract_url(text: str) -> str:
    """Extract URL from text message."""
    # Try to find a URL in the text using regex
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    match = re.search(url_pattern, text)
    
    if match:
        return match.group(0)
    
    # If no http(s), look for domain patterns
    for domain in ['youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com', 
                   'twitter.com', 'x.com', 'facebook.com', 'fb.watch', 'smule.com']:
        if domain in text.lower():
            # Try to extract something that looks like a URL around the domain
            pattern = rf'(?:https?://)?(?:www\.)?{re.escape(domain)}[^\s<>"{{}}|\\^`\[\]]*'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(0)
                # Add https:// if missing
                if not url.startswith('http'):
                    url = 'https://' + url
                return url
    
    return text  # Return original if no URL found


async def download_video(url: str, user_id: int) -> tuple[str, str]:
    """
    Download video from URL.
    
    Returns:
        tuple: (video_path, error_message)
        - If successful: (path_to_video, None)
        - If failed: (None, error_message)
    """
    # Check if it's a Smule URL and handle separately
    if 'smule.com' in url.lower():
        return await download_smule_video(url, user_id)
    
    # Check if it's an Instagram URL and handle separately
    if 'instagram.com' in url.lower():
        return await download_instagram_video(url, user_id)
    
    output_template = os.path.join(DOWNLOADS_DIR, f"{user_id}_%(id)s.%(ext)s")
    
    # yt-dlp options
    ydl_opts = {
        'format': 'best[filesize<50M]/best',  # Try to get best quality under 50MB
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        # Convert to mp4 if needed
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        # Merge video and audio if separate
        'merge_output_format': 'mp4',
    }
    
    try:
        # Run yt-dlp in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        video_path = await asyncio.wait_for(
            loop.run_in_executor(None, _download_sync, url, ydl_opts),
            timeout=DOWNLOAD_TIMEOUT
        )
        
        # Check file size
        if os.path.exists(video_path):
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                os.remove(video_path)
                return None, f"Video too large: {file_size_mb:.1f}MB"
            
            return video_path, None
        else:
            return None, "Download failed: File not created"
    
    except asyncio.TimeoutError:
        return None, "Download timeout exceeded"
    except Exception as e:
        error_msg = str(e)
        # Clean up any partial downloads
        _cleanup_partial_downloads(user_id)
        return None, error_msg


def _download_sync(url: str, ydl_opts: dict) -> str:
    """
    Synchronous download function to be run in executor.
    
    Returns:
        str: Path to downloaded video file
    """
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract info to get the output filename
        info = ydl.extract_info(url, download=True)
        
        # Get the actual filename
        if 'requested_downloads' in info and info['requested_downloads']:
            filename = info['requested_downloads'][0]['filepath']
        else:
            # Fallback: construct filename from template
            filename = ydl.prepare_filename(info)
        
        return filename


def _cleanup_partial_downloads(user_id: int):
    """Remove any partial download files for a user."""
    try:
        downloads_path = Path(DOWNLOADS_DIR)
        for file in downloads_path.glob(f"{user_id}_*"):
            try:
                file.unlink()
            except Exception:
                pass
    except Exception:
        pass


def _download_smule_with_ytdlp(url: str, ydl_opts: dict) -> bool:
    """Try downloading Smule with yt-dlp."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            return True
    except:
        return False


async def download_instagram_video(url: str, user_id: int) -> tuple[str, str]:
    """
    Download video from Instagram using snapinsta service.
    
    Returns:
        tuple: (video_path, error_message)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Extract post ID from URL
        post_id_match = re.search(r'(?:reel|p)/([A-Za-z0-9_-]+)', url)
        if not post_id_match:
            return None, "Invalid Instagram URL format"
        
        post_id = post_id_match.group(1)
        output_path = os.path.join(DOWNLOADS_DIR, f"{user_id}_instagram_{post_id}.mp4")
        
        loop = asyncio.get_event_loop()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # Try snapinsta.app
        logger.info(f"Trying snapinsta for Instagram: {post_id}")
        snapinsta_url = f"https://snapinsta.app/api/ajaxSearch"
        
        post_data = {
            'q': url,
            't': 'media',
            'lang': 'en'
        }
        
        try:
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(snapinsta_url, data=post_data, headers=headers, timeout=15)
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Look for video URL in response
                video_url = None
                if 'data' in data:
                    html_content = data.get('data', '')
                    # Find download link in HTML
                    video_match = re.search(r'href="([^"]+)"[^>]*download[^>]*>.*?Download', html_content, re.IGNORECASE | re.DOTALL)
                    if video_match:
                        video_url = video_match.group(1)
                        logger.info(f"Found Instagram video URL: {video_url[:100]}")
                
                if video_url:
                    # Download the video
                    media_response = await loop.run_in_executor(
                        None,
                        lambda: requests.get(video_url, stream=True, timeout=DOWNLOAD_TIMEOUT, headers=headers)
                    )
                    
                    if media_response.status_code == 200:
                        downloaded_size = 0
                        with open(output_path, 'wb') as f:
                            for chunk in media_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    downloaded_size += len(chunk)
                                    
                                    if downloaded_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                                        os.remove(output_path)
                                        return None, f"File too large (over {MAX_FILE_SIZE_MB}MB)"
                        
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                            logger.info(f"Successfully downloaded Instagram video")
                            return output_path, None
        except Exception as e:
            logger.warning(f"Snapinsta failed: {str(e)}, trying alternative...")
        
        # Try alternative: instadownloader.co
        logger.info(f"Trying instadownloader.co for Instagram")
        alt_url = f"https://v3.instadownloader.co/api/ajaxSearch"
        
        try:
            alt_response = await loop.run_in_executor(
                None,
                lambda: requests.post(alt_url, data={'q': url, 't': 'media'}, headers=headers, timeout=15)
            )
            
            if alt_response.status_code == 200:
                alt_data = alt_response.json()
                
                if 'data' in alt_data:
                    html_content = alt_data.get('data', '')
                    video_match = re.search(r'href="([^"]+)"[^>]*download', html_content, re.IGNORECASE)
                    if video_match:
                        video_url = video_match.group(1)
                        logger.info(f"Found Instagram video URL via alternative: {video_url[:100]}")
                        
                        # Download
                        media_response = await loop.run_in_executor(
                            None,
                            lambda: requests.get(video_url, stream=True, timeout=DOWNLOAD_TIMEOUT, headers=headers)
                        )
                        
                        if media_response.status_code == 200:
                            downloaded_size = 0
                            with open(output_path, 'wb') as f:
                                for chunk in media_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded_size += len(chunk)
                                        
                                        if downloaded_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                                            os.remove(output_path)
                                            return None, f"File too large (over {MAX_FILE_SIZE_MB}MB)"
                            
                            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                                logger.info(f"Successfully downloaded Instagram video via alternative")
                                return output_path, None
        except Exception as e:
            logger.warning(f"Alternative service failed: {str(e)}")
        
        # If both services fail, return error
        logger.error("Instagram download failed - all services unavailable")
        return None, "Instagram download temporarily unavailable. The post might be private or Instagram is blocking downloads."
        
    except Exception as e:
        logger.error(f"Instagram download error: {str(e)}")
        _cleanup_partial_downloads(user_id)
        return None, f"Failed to download from Instagram: {str(e)}"


async def download_smule_video(url: str, user_id: int) -> tuple[str, str]:
    """
    Download video from Smule using smule-downloader CLI tool.
    
    Returns:
        tuple: (video_path, error_message)
    """
    try:
        # Extract recording ID from URL
        recording_id_match = re.search(r'(\d+_\d+)', url)
        if not recording_id_match:
            return None, "Invalid Smule URL format"
        
        recording_id = recording_id_match.group(1)
        output_path = os.path.join(DOWNLOADS_DIR, f"{user_id}_smule_{recording_id}.mp4")
        
        loop = asyncio.get_event_loop()
        
        # Try direct CDN URLs FIRST (most reliable method for Smule)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        cdn_urls = [
            f"https://c-fa.smule.com/{recording_id}.m4a",
            f"https://c-fa.smule.com/{recording_id}.mp4",
            f"https://c-fa-hp.smule.com/{recording_id}.m4a",
            f"https://c-fa-hp.smule.com/{recording_id}.mp4",
            f"https://c-sf-l.smule.com/{recording_id}.m4a",
            f"https://sing-avatar.smule.com/{recording_id}.m4a",
        ]
        
        import logging
        logger = logging.getLogger(__name__)
        
        # CDN URLs don't work anymore, skip directly to scraping
        logger.info(f"Starting Smule download for recording: {recording_id}")
        
        # Try using sownloader.com service (used by many Smule downloaders)
        try:
            sownloader_url = f"https://sownloader.com/index.php?url={url}"
            logger.info(f"Trying sownloader.com service")
            
            sownloader_response = await loop.run_in_executor(
                None,
                lambda: requests.get(sownloader_url, timeout=15, headers=headers)
            )
            
            if sownloader_response.status_code == 200:
                sownloader_html = sownloader_response.text
                video_url = None
                
                # Look for download links in the page (updated CDN domain)
                # Pattern 1: c-cdnet.cdn.smule.com (new CDN)
                video_pattern = r'href=["\']([^"\']*c-cdnet\.cdn\.smule\.com[^"\']*\.mp4[^"\']*)["\']'
                video_match = re.search(video_pattern, sownloader_html)
                
                if video_match:
                    video_url = video_match.group(1)
                    logger.info(f"Found video URL: {video_url[:100]}")
                
                # Pattern 2: Audio links if no video
                if not video_url:
                    audio_pattern = r'href=["\']([^"\']*c-cdnet\.cdn\.smule\.com[^"\']*\.m4a[^"\']*)["\']'
                    audio_match = re.search(audio_pattern, sownloader_html)
                    if audio_match:
                        video_url = audio_match.group(1)
                        logger.info(f"Found audio URL: {audio_url[:100]}")
                
                # Pattern 3: Look in any context for new smule CDN URLs
                if not video_url:
                    generic_pattern = r'(https://c-cdnet\.cdn\.smule\.com/[^\s"\'<>]+\.(?:mp4|m4a))'
                    generic_match = re.search(generic_pattern, sownloader_html)
                    if generic_match:
                        video_url = generic_match.group(1)
                        logger.info(f"Found media URL: {video_url[:100]}")
                
                # Pattern 4: Try old CDN domain as fallback
                if not video_url:
                    old_cdn_pattern = r'(https://c-cl\.cdn\.smule\.com/[^\s"\'<>]+\.(?:mp4|m4a))'
                    old_match = re.search(old_cdn_pattern, sownloader_html)
                    if old_match:
                        video_url = old_match.group(1)
                        logger.info(f"Found media URL (old CDN): {video_url[:100]}")
                        
                if video_url:
                    # Download from the CDN URL
                    media_response = await loop.run_in_executor(
                        None,
                        lambda: requests.get(video_url, stream=True, timeout=DOWNLOAD_TIMEOUT)
                    )
                    
                    if media_response.status_code == 200:
                        downloaded_size = 0
                        with open(output_path, 'wb') as f:
                            for chunk in media_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    downloaded_size += len(chunk)
                                    
                                    if downloaded_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                                        os.remove(output_path)
                                        return None, f"File too large (over {MAX_FILE_SIZE_MB}MB)"
                        
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                            logger.info(f"Successfully downloaded via sownloader")
                            return output_path, None
        except Exception as e:
            logger.error(f"Sownloader method failed: {str(e)}")
        
        # If sownloader fails, try direct scraping
        clean_url = url.split('?')[0]
        
        # Try to convert recording URL to sing-recording format which might work better
        if '/recording/' in clean_url:
            # Convert: https://www.smule.com/recording/.../1234_5678/... 
            # To: https://www.smule.com/sing-recording/1234_5678
            clean_url = f"https://www.smule.com/sing-recording/{recording_id}"
        
        # Fetch the page HTML with realistic browser headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.smule.com/',
        }
        
        # Create a session to maintain cookies
        session = requests.Session()
        
        response = await loop.run_in_executor(
            None,
            lambda: session.get(clean_url, headers=headers, timeout=15, allow_redirects=True)
        )
        
        if response.status_code == 418:
            # Try direct CDN URL construction (common pattern for Smule)
            cdn_urls = [
                f"https://c-fa.smule.com/{recording_id}.m4a",
                f"https://c-fa.smule.com/{recording_id}.mp4",
                f"https://c-fa-hp.smule.com/{recording_id}.m4a",
            ]
            
            for cdn_url in cdn_urls:
                try:
                    cdn_response = await loop.run_in_executor(
                        None,
                        lambda url=cdn_url: session.get(url, stream=True, timeout=10, headers=headers)
                    )
                    if cdn_response.status_code == 200:
                        # Found working CDN URL, download it
                        with open(output_path, 'wb') as f:
                            for chunk in cdn_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            return output_path, None
                except:
                    continue
            
            return None, "Smule blocked the request. Please try a different link or contact support."
        
        if response.status_code != 200:
            return None, f"Failed to access Smule page (status {response.status_code})"
        
        html = response.text
        logger.info(f"Successfully fetched Smule page, size: {len(html)} bytes")
        
        # Look for JSON data embedded in the page
        video_url = None
        
        # Try to find __PRELOADED_STATE__ or similar embedded JSON
        json_match = re.search(r'__PRELOADED_STATE__\s*=\s*(\{.+?\});', html, re.DOTALL)
        if json_match:
            try:
                import json
                data = json.loads(json_match.group(1))
                logger.info(f"Found PRELOADED_STATE data")
                # Navigate through the data structure to find media URLs
                # This structure may vary, log it to see
                logger.info(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            except:
                pass
        
        # Try multiple patterns to find video URL (only accept valid HTTP/HTTPS URLs)
        
        # Try multiple patterns to find video URL (only accept valid HTTP/HTTPS URLs)
        
        # Pattern 1: Look for video_media_mp4_url
        mp4_match = re.search(r'"(?:video_media_mp4_url|videoMediaMp4Url)"\s*:\s*"(https?://[^"]+)"', html)
        if mp4_match:
            video_url = mp4_match.group(1)
            logger.info(f"Found video_media_mp4_url: {video_url[:100]}")
        
        # Pattern 2: Look for video_media_url  
        if not video_url:
            media_match = re.search(r'"(?:video_media_url|videoMediaUrl)"\s*:\s*"(https?://[^"]+)"', html)
            if media_match:
                video_url = media_match.group(1)
                logger.info(f"Found video_media_url: {video_url[:100]}")
        
        # Pattern 3: Look for media_url (audio recordings)
        if not video_url:
            generic_match = re.search(r'"(?:media_url|mediaUrl)"\s*:\s*"(https?://[^"]+)"', html)
            if generic_match:
                video_url = generic_match.group(1)
                logger.info(f"Found media_url: {video_url[:100]}")
        
        # Pattern 4: Look for any smule media URLs in the page
        if not video_url:
            smule_url_match = re.search(r'(https://[a-z0-9\-]+\.smule\.com/[^\s"\'<>]+\.(?:m4a|mp4|mp3))', html)
            if smule_url_match:
                video_url = smule_url_match.group(1)
                logger.info(f"Found smule media URL: {video_url[:100]}")
        
        if not video_url:
            logger.error("No media URL found in page")
            return None, "Could not find media URL in Smule page. Try a different recording or use the Smule app to download."
        
        if not video_url:
            return None, "Could not find video URL in Smule page. The recording might be audio-only or private."
        
        # Clean up URL (unescape if needed)
        video_url = video_url.replace('\\/', '/')
        
        # Extract recording ID for filename
        recording_id_match = re.search(r'(\d+_\d+)', url)
        recording_id = recording_id_match.group(1) if recording_id_match else "smule"
        
        # Download the video/audio file
        output_path = os.path.join(DOWNLOADS_DIR, f"{user_id}_smule_{recording_id}.mp4")
        
        video_response = await loop.run_in_executor(
            None,
            lambda: session.get(video_url, stream=True, timeout=DOWNLOAD_TIMEOUT, headers=headers)
        )
        
        if video_response.status_code != 200:
            return None, "Failed to download video from Smule"
        
        # Check content length if available
        content_length = video_response.headers.get('content-length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                return None, f"Video too large: {size_mb:.1f}MB"
        
        # Download in chunks and check size
        downloaded_size = 0
        with open(output_path, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Check if exceeding size limit
                    if downloaded_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                        os.remove(output_path)
                        return None, f"Video too large (over {MAX_FILE_SIZE_MB}MB)"
        
        return output_path, None
        
    except asyncio.TimeoutError:
        return None, "Download timeout"
    except Exception as e:
        _cleanup_partial_downloads(user_id)
        return None, f"Smule download error: {str(e)}"
