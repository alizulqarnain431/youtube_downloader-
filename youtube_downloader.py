import os
import sys
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar,
                             QFileDialog, QMessageBox, QGroupBox, QCheckBox, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QPalette, QColor
import yt_dlp


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    error_signal = pyqtSignal(str)
    playlist_info_signal = pyqtSignal(str, int)
    log_signal = pyqtSignal(str)

    def __init__(self, url, options, is_playlist=False):
        super().__init__()
        self.url = url
        self.options = options
        self.is_playlist = is_playlist
        self.running = True

    def run(self):
        try:
            with yt_dlp.YoutubeDL(self.options) as ydl:
                if self.is_playlist:
                    # Extract playlist info first
                    info = ydl.extract_info(self.url, download=False)
                    if 'entries' in info:
                        playlist_title = info.get('title', 'playlist')
                        num_entries = len(info['entries'])
                        self.playlist_info_signal.emit(playlist_title, num_entries)
                
                ydl.download([self.url])
            self.finished_signal.emit(True, "Download completed successfully!")
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.running = False

    def stop(self):
        self.running = False


class YTDLLogger(QObject):
    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal

    def debug(self, msg):
        if msg.startswith('[debug] '):
            pass
        else:
            self.log_signal.emit(msg)

    def info(self, msg):
        self.log_signal.emit(msg)

    def warning(self, msg):
        self.log_signal.emit(f"WARNING: {msg}")

    def error(self, msg):
        self.log_signal.emit(f"ERROR: {msg}")


class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced YouTube Downloader")
        self.setGeometry(100, 100, 800, 650)  # Increased window size
        self.default_palette = QApplication.palette()
        self.cookies_file = None
        self.init_ui()
        self.download_thread = None
        self.current_playlist_folder = ""
        self.current_download_count = 0
        self.total_playlist_items = 0

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Theme Toggle
        theme_layout = QHBoxLayout()
        self.theme_check = QCheckBox("Dark Theme")
        self.theme_check.stateChanged.connect(self.toggle_theme)
        theme_layout.addStretch()
        theme_layout.addWidget(self.theme_check)
        main_layout.addLayout(theme_layout)

        # URL Input Section
        url_group = QGroupBox("Video/Playlist URL")
        url_layout = QVBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube video or playlist URL...")
        url_layout.addWidget(self.url_input)
        
        # Playlist Options
        playlist_layout = QHBoxLayout()
        self.playlist_check = QCheckBox("Download as Playlist")
        self.playlist_range = QLineEdit()
        self.playlist_range.setPlaceholderText("e.g., 1-10 or 1,3,5 (leave empty for all)")
        self.playlist_range.setEnabled(False)
        self.playlist_check.stateChanged.connect(lambda: self.playlist_range.setEnabled(self.playlist_check.isChecked()))
        
        playlist_layout.addWidget(self.playlist_check)
        playlist_layout.addWidget(self.playlist_range)
        url_layout.addLayout(playlist_layout)
        url_group.setLayout(url_layout)

        # Download Options Section
        options_group = QGroupBox("Download Options")
        options_layout = QVBoxLayout()

        # Quality Selection
        quality_layout = QHBoxLayout()
        quality_label = QLabel("Resolution:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best Available", "8K", "4K", "2K", "1080p", "720p", "480p", "360p"])
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        options_layout.addLayout(quality_layout)

        # Format Selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Content Type:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Video+Audio", "Video Only", "Audio Only"])
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        options_layout.addLayout(format_layout)

        # Output Format Selection
        output_format_layout = QHBoxLayout()
        output_format_label = QLabel("Output Format:")
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["MP4", "MKV", "WEBM", "AAC", "MP3", "Best Available"])
        output_format_layout.addWidget(output_format_label)
        output_format_layout.addWidget(self.output_format_combo)
        options_layout.addLayout(output_format_layout)

        # Additional Options
        options_row1 = QHBoxLayout()
        self.subtitles_check = QCheckBox("Download Subtitles")
        self.thumbnail_check = QCheckBox("Download Thumbnail")
        options_row1.addWidget(self.subtitles_check)
        options_row1.addWidget(self.thumbnail_check)
        options_layout.addLayout(options_row1)

        options_row2 = QHBoxLayout()
        self.metadata_check = QCheckBox("Add Metadata")
        self.metadata_check.setChecked(True)
        self.embed_thumbnail_check = QCheckBox("Embed Thumbnail")
        options_row2.addWidget(self.metadata_check)
        options_row2.addWidget(self.embed_thumbnail_check)
        options_layout.addLayout(options_row2)
        
        # Cookie support
        cookie_layout = QHBoxLayout()
        self.cookie_check = QCheckBox("Use Cookies")
        self.cookie_check.stateChanged.connect(self.toggle_cookie_ui)
        self.cookie_path = QLineEdit()
        self.cookie_path.setPlaceholderText("Path to cookies file (Netscape format or browser)")
        self.cookie_path.setEnabled(False)
        self.browse_cookie_btn = QPushButton("Browse")
        self.browse_cookie_btn.setEnabled(False)
        self.browse_cookie_btn.clicked.connect(self.select_cookie_file)
        
        cookie_layout.addWidget(self.cookie_check)
        cookie_layout.addWidget(self.cookie_path)
        cookie_layout.addWidget(self.browse_cookie_btn)
        options_layout.addLayout(cookie_layout)
        
        options_group.setLayout(options_layout)

        # Output Location
        output_group = QGroupBox("Output Location")
        output_layout = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Select download directory...")
        self.output_input.setText(os.path.expanduser("~/Downloads"))
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(browse_btn)
        output_group.setLayout(output_layout)

        # Progress Bar and Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        self.status_label = QLabel("Ready to download")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold;")

        # Log Console
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(150)  # Increased height
        self.log_console.setPlaceholderText("Download logs will appear here...")

        # Download Button
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.start_download)

        # Add widgets to main layout
        main_layout.addWidget(url_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(output_group)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.log_console)
        main_layout.addWidget(self.download_btn)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Connect format combo change to update output formats
        self.format_combo.currentTextChanged.connect(self.update_output_formats)
        self.update_output_formats()

    def toggle_cookie_ui(self, state):
        enabled = state == Qt.Checked
        self.cookie_path.setEnabled(enabled)
        self.browse_cookie_btn.setEnabled(enabled)

    def select_cookie_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Cookies File", 
            "", 
            "Cookies Files (*.txt *.json);;All Files (*)"
        )
        if file_path:
            self.cookie_path.setText(file_path)
            self.cookies_file = file_path

    def update_output_formats(self):
        current_format = self.format_combo.currentText()
        self.output_format_combo.clear()
        
        if current_format == "Video+Audio":
            self.output_format_combo.addItems(["MP4", "MKV", "WEBM", "Best Available"])
        elif current_format == "Video Only":
            self.output_format_combo.addItems(["MP4", "MKV", "WEBM", "Best Available"])
        elif current_format == "Audio Only":
            self.output_format_combo.addItems(["MP3", "AAC", "M4A", "OPUS", "Best Available"])
        
        # Enable/disable thumbnail embedding based on format
        self.embed_thumbnail_check.setEnabled(current_format != "Audio Only")

    def toggle_theme(self, state):
        if state == Qt.Checked:
            # Set dark theme
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.WindowText, Qt.white)
            dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
            dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
            dark_palette.setColor(QPalette.ToolTipText, Qt.white)
            dark_palette.setColor(QPalette.Text, Qt.white)
            dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ButtonText, Qt.white)
            dark_palette.setColor(QPalette.BrightText, Qt.red)
            dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.HighlightedText, Qt.black)
            QApplication.setPalette(dark_palette)
        else:
            # Set light theme
            QApplication.setPalette(self.default_palette)

    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if directory:
            self.output_input.setText(directory)

    def get_quality_options(self, quality):
        quality_map = {
            "Best Available": "best",
            "8K": "4320",
            "4K": "2160",
            "2K": "1440",
            "1080p": "1080",
            "720p": "720",
            "480p": "480",
            "360p": "360"
        }
        return quality_map.get(quality, "best")

    def get_format_extension(self):
        format_map = {
            "MP4": "mp4",
            "MKV": "mkv",
            "WEBM": "webm",
            "MP3": "mp3",
            "AAC": "aac",
            "M4A": "m4a",
            "OPUS": "opus",
            "Best Available": "best"
        }
        return format_map.get(self.output_format_combo.currentText(), "best")

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return

        if not self.output_input.text():
            QMessageBox.warning(self, "Error", "Please select an output directory")
            return

        is_playlist = self.playlist_check.isChecked()
        output_path = self.output_input.text()
        
        # For playlists, create a subfolder
        if is_playlist:
            # Temporarily set output to main directory to extract playlist info
            temp_output = os.path.join(output_path, "temp_playlist_folder")
            options = {
                'outtmpl': os.path.join(temp_output, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True
            }
            
            # First extract playlist info to get the title
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if 'entries' in info:
                        playlist_title = info.get('title', 'playlist')
                        # Clean the playlist title to make it filesystem-safe
                        playlist_title = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in playlist_title)
                        self.current_playlist_folder = os.path.join(output_path, playlist_title)
                        os.makedirs(self.current_playlist_folder, exist_ok=True)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Couldn't get playlist info: {str(e)}")
                return

            output_path = self.current_playlist_folder
            self.current_download_count = 0
            self.status_label.setText(f"Preparing to download playlist: {playlist_title}")

        # Prepare final download options
        final_output = os.path.join(output_path, '%(title)s.%(ext)s')
        quality = self.quality_combo.currentText()
        format_choice = self.format_combo.currentText()
        output_format = self.get_format_extension()

        options = {
            'outtmpl': final_output,
            'progress_hooks': [self.progress_hook],
            'quiet': False,
            'no_warnings': False,
            'restrictfilenames': True,
            'writesubtitles': self.subtitles_check.isChecked(),
            'writeautomaticsub': self.subtitles_check.isChecked(),
            'writethumbnail': self.thumbnail_check.isChecked(),
            'addmetadata': self.metadata_check.isChecked(),
            'format': self.get_format_string(quality, format_choice, output_format),
            'postprocessors': [],
            'cookiefile': self.cookie_path.text() if self.cookie_check.isChecked() and self.cookie_path.text() else None
        }

        # Set output format options
        if output_format in ["mp4", "mkv", "webm"] and output_format != "best":
            options['merge_output_format'] = output_format

        # Add thumbnail embedding if requested
        if self.embed_thumbnail_check.isChecked() and format_choice != "Audio Only":
            options['postprocessors'].append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False
            })

        # Add metadata postprocessor for audio files
        if format_choice == "Audio Only" and self.metadata_check.isChecked():
            options['postprocessors'].append({
                'key': 'FFmpegMetadata'
            })

        if is_playlist:
            playlist_range = self.playlist_range.text().strip()
            if playlist_range:
                options['playlist_items'] = playlist_range

        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_console.clear()

        self.download_thread = DownloadThread(url, options, is_playlist)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.show_error)
        self.download_thread.playlist_info_signal.connect(self.update_playlist_info)
        self.download_thread.log_signal.connect(self.log_message)
        
        # Create logger and pass it the log signal
        options['logger'] = YTDLLogger(self.download_thread.log_signal)
        
        self.download_thread.start()

    @pyqtSlot(str)
    def log_message(self, msg):
        self.log_console.append(msg.strip())
        # Auto-scroll to bottom
        scroll_bar = self.log_console.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def update_playlist_info(self, playlist_title, total_items):
        self.total_playlist_items = total_items
        self.status_label.setText(f"Downloading playlist: {playlist_title} (0/{total_items})")

    def get_format_string(self, quality, format_choice, output_format):
        quality_code = self.get_quality_options(quality)
        
        if format_choice == "Video+Audio":
            if quality == "Best Available":
                if output_format == "best":
                    return "bestvideo+bestaudio"
                else:
                    return f"bestvideo[ext={output_format}]+bestaudio[ext={output_format}]/bestvideo+bestaudio"
            else:
                return f"bestvideo[height<={quality_code}][ext={output_format}]+bestaudio[ext={output_format}]/best[height<={quality_code}]"
        elif format_choice == "Video Only":
            if quality == "Best Available":
                if output_format == "best":
                    return "bestvideo"
                else:
                    return f"bestvideo[ext={output_format}]"
            else:
                return f"bestvideo[height<={quality_code}][ext={output_format}]"
        elif format_choice == "Audio Only":
            if output_format == "best":
                return "bestaudio"
            else:
                return f"bestaudio[ext={output_format}]"
        return "best"

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percent = int(d['downloaded_bytes'] / total_bytes * 100)
                filename = os.path.basename(d.get('filename', ''))
                self.download_thread.progress_signal.emit(percent, filename)
        elif d['status'] == 'finished':
            self.download_thread.progress_signal.emit(100, "Download complete")
            if self.playlist_check.isChecked():
                self.current_download_count += 1
                self.status_label.setText(
                    f"Downloading playlist item {self.current_download_count}/{self.total_playlist_items}"
                )

    @pyqtSlot(int, str)
    def update_progress(self, percent, status):
        self.progress_bar.setValue(percent)
        if status:
            self.status_label.setText(status)

    @pyqtSlot(bool, str)
    def download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
            self.status_label.setText("Ready to download")
            self.progress_bar.setValue(0)
        else:
            QMessageBox.warning(self, "Error", message)

    @pyqtSlot(str)
    def show_error(self, error_msg):
        self.download_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Download failed: {error_msg}")
        self.status_label.setText("Download failed")

    def closeEvent(self, event):
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Download in Progress',
                "A download is in progress. Are you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.download_thread.stop()
                self.download_thread.quit()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    downloader = YouTubeDownloader()
    downloader.show()
    sys.exit(app.exec_())
