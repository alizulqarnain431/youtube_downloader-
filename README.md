Advanced YouTube Downloader
A Python-based desktop application built with PyQt5 and yt-dlp for downloading YouTube videos and playlists with advanced features.
Features

Download YouTube videos and playlists
Choose video quality (360p to 8K)
Select content type (Video+Audio, Video Only, Audio Only)
Support for multiple output formats (MP4, MKV, WEBM, MP3, AAC, etc.)
Download subtitles and thumbnails
Add metadata to downloaded files
Embed thumbnails in videos
Support for cookies (Netscape format or browser cookies)
Playlist download with range selection
Dark/Light theme toggle
Progress bar and detailed download logs
Custom output directory selection

Installation

Clone the repository:

git clone https://github.com/alizulqarnain431/youtube_downloader-
cd youtube_downloader


Install the required dependencies:

pip install -r requirements.txt


Run the application:

python youtube_downloader.py

Requirements
See requirements.txt for the list of required Python packages.
Usage

Launch the application.
Enter a YouTube video or playlist URL.
Select desired options:
Resolution (Best Available, 8K, 4K, etc.)
Content Type (Video+Audio, Video Only, Audio Only)
Output Format
Additional options (subtitles, thumbnails, metadata, etc.)
Output directory


For playlists, optionally specify a range (e.g., "1-5" or "1,3,5").
Click "Download" to start the download process.
Monitor progress via the progress bar and log console.

Notes

Ensure you have a stable internet connection.
For restricted content, you may need to provide a cookies file.
The application creates a subfolder for playlist downloads using the playlist title.
Downloads can be canceled by closing the application (with confirmation).

License
This project is licensed under the MIT License.
