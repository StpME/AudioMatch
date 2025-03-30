import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QProgressBar, QTableWidget,
                            QTableWidgetItem, QHeaderView, QGroupBox, QButtonGroup, 
                            QRadioButton, QMessageBox)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from runner import Runner
import librosa
# import numpy as np
# np.random.seed(42)

class ComparisonGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.original_files = []
        self.remastered_files = []
        self.init_ui()
        
        self.results = []

        self.runner = None

    def init_ui(self):
        self.setWindowTitle('Audio Matcher')
        self.setGeometry(100, 100, 1200, 800)
        
        main_widget = QWidget()
        layout = QVBoxLayout()

        
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        
        # Selection type
        self.selection_group = QButtonGroup()
        rb_layout = QHBoxLayout()
        self.file_rb = QRadioButton("Select Files")
        self.folder_rb = QRadioButton("Select Folders")
        self.file_rb.setChecked(True)
        self.selection_group.addButton(self.file_rb)
        self.selection_group.addButton(self.folder_rb)
        rb_layout.addWidget(self.file_rb)
        rb_layout.addWidget(self.folder_rb)
        file_layout.addLayout(rb_layout)

        # Original files
        orig_layout = QHBoxLayout()
        self.orig_label = QLabel("Original Files: None selected")
        self.orig_btn = QPushButton("Select Originals")
        self.orig_btn.clicked.connect(self.select_originals)
        orig_layout.addWidget(self.orig_label)
        orig_layout.addWidget(self.orig_btn)
        
        # Remastered files
        remastered_layout = QHBoxLayout()
        self.remastered_label = QLabel("Remastered Files: None selected")
        self.remastered_btn = QPushButton("Select Remastered")
        self.remastered_btn.clicked.connect(self.select_remastered)
        remastered_layout.addWidget(self.remastered_label)
        remastered_layout.addWidget(self.remastered_btn)
        
        file_layout.addLayout(orig_layout)
        file_layout.addLayout(remastered_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Results table
        self.table = QTableWidget()


        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Make cells non-editable
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)  # Remove focus border
        # Custom styling for selection
        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #e0e0e0;
                color: black;
            }
            QTableCornerButton::section {
                background-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: white;
                border: none;
            }
        """)







        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Remastered","Original",
                                              "Confidence", "Remaster Duration", "Original Duration"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)





        # Disable header interactions
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionsClickable(False)
        
        vertical_header = self.table.verticalHeader()
        vertical_header.setVisible(False)  # Hide row #s
        vertical_header.setSectionResizeMode(QHeaderView.Fixed)
        vertical_header.setDefaultSectionSize(1)


        
        # Progress bar
        self.progress = QProgressBar()
        self.status_label = QLabel("Ready")
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Comparison")
        self.start_btn.clicked.connect(self.start_comparison)
        self.export_btn = QPushButton("Export Results")
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        self.diagnose_btn = QPushButton("Diagnose MP3")
        self.diagnose_btn.clicked.connect(self.diagnose_mp3)
        btn_layout.addWidget(self.diagnose_btn)
        
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def select_originals(self):
        if self.folder_rb.isChecked():
            path = QFileDialog.getExistingDirectory(self, "Select Original Folder")
            if path:
                self.original_files = self.scan_audio_files(path)
                self.orig_label.setText(f"Original Files: {len(self.original_files)} in folder")
                # Verify if any audio files found
                if not self.original_files:
                    QMessageBox.warning(self, "Warning", 
                                    f"No audio files found in {path}.\n"
                                    "Check that the folder contains supported audio files.")
        else:
            files, _ = QFileDialog.getOpenFileNames(
                self, 
                "Select Original Files", 
                "", 
                "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a)"
            )
            if files: 
                # Verify each file exists (plan to make it stop if one fails so it doesnt send bunch of error boxes and crash)
                valid_files = [f for f in files if os.path.exists(f)]
                if len(valid_files) != len(files):
                    QMessageBox.warning(self, "Warning", 
                                    f"{len(files) - len(valid_files)} files could not be accessed.")
                
                self.original_files = valid_files
                self.orig_label.setText(f"Original Files: {len(valid_files)} selected")

    def select_remastered(self):
        if self.folder_rb.isChecked():
            path = QFileDialog.getExistingDirectory(self, "Select Remastered Folder")
            if path:
                self.remastered_files = self.scan_audio_files(path)
                self.remastered_label.setText(f"Remastered Files: {len(self.remastered_files)} in folder")
        else:
            files, _ = QFileDialog.getOpenFileNames(self, "Select Remastered Files", "", 
                                                  "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a)")
            if files:
                self.remastered_files = files
                self.remastered_label.setText(f"Remastered Files: {len(files)} selected")




    def scan_audio_files(self, folder):
        audio_files = []
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):
                    audio_files.append(os.path.join(root, file))
        return audio_files
    


    

    def start_comparison(self):
        if not self.original_files or not self.remastered_files:
            QMessageBox.warning(self, "Error", "Please select both original and remastered files")
            return
        print("Original files:")
        for path in self.original_files:
            print(f" - {path} (exists: {os.path.exists(path)})")
        
        print("Remastered files:")
        for path in self.remastered_files:
            print(f" - {path} (exists: {os.path.exists(path)})")
        
        # Disable UI when processing
        self.start_btn.setEnabled(False)
        self.orig_btn.setEnabled(False)
        self.remastered_btn.setEnabled(False)
        
        self.progress.setValue(0)
        self.status_label.setText("Starting comparison...")
        self.table.setRowCount(0)
        
        self.runner = Runner(self.original_files, self.remastered_files)
        self.runner.progress_updated.connect(self.update_progress)
        self.runner.matches_found.connect(self.show_results)
        self.runner.error_occurred.connect(self.show_error)
        self.runner.finished.connect(self.on_runner_finished)
        self.runner.start()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_label.setText(message)

    def show_error(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)
        if self.runner:
            self.runner.stop()

    def on_runner_finished(self):
        # Re-enable UI
        self.start_btn.setEnabled(True)
        self.orig_btn.setEnabled(True)
        self.remastered_btn.setEnabled(True)
        self.runner = None

    def show_results(self, results):
        self.results = results
        self.table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            remastered_name = os.path.basename(result['path'])
            self.table.setItem(row, 0, QTableWidgetItem(remastered_name))
            self.table.setItem(row, 1, QTableWidgetItem(result['match']))
            
            # Duration cols
            self.table.setItem(row, 3, QTableWidgetItem(self.format_duration(result['rem_duration'])))
            self.table.setItem(row, 4, QTableWidgetItem(
                self.format_duration(result['orig_duration']) if result['orig_duration'] > 0 else "N/A"
            ))
            
            # Confidence col
            conf_item = QTableWidgetItem(f"{result['confidence']:.2f}")
            conf_item.setBackground(self.confidence_color(result['confidence']))
            self.table.setItem(row, 2, conf_item)

        # Connect click events after populating table
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.cellClicked.connect(self.on_cell_clicked)
        
        match_count = len([r for r in results if r['confidence'] > 0.3])
        self.status_label.setText(f"Found {match_count} matches out of {len(results)} files")






    def on_cell_clicked(self, row, column):
        """Handle single clicks for highlighting"""
        if column in (0, 1):
            self.table.clearSelection()
            item = self.table.item(row, column)
            if item:
                item.setSelected(True)
        else:
            self.table.clearSelection()





    def on_cell_double_clicked(self, row, column):
        """Handle cell clicks in the results table"""
        if 0 <= row < len(self.results):
            result = self.results[row]
            
            # Determine which file to open based on clicked column
            if column == 0:  # Remastered column
                file_path = result['path']
            elif column == 1:  # Original column
                file_path = result.get('orig_path', '')
            else:
                return

            # Open the file if path exists
            if file_path and os.path.exists(file_path):
                self.open_file(file_path)

    @staticmethod
    def open_file(path):
        """Open file with default application"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(path)
        except Exception as e:
            QMessageBox.warning(None, "Open Error", 
                              f"Could not open file:\n{path}\nError: {str(e)}")

    # Color for different tiers of confidence
    def confidence_color(self, confidence):
        if confidence >= 0.7:
            return QColor(144, 238, 144)  # Light green
        elif confidence >= 0.5:
            return QColor(255, 255, 224)  # Light yellow
        elif confidence >= 0.3:
            return QColor(255, 228, 181)  # Light orange
        else:
            return QColor(255, 182, 193)  # Light red
        
    @staticmethod
    def format_duration(seconds):
        """Convert seconds to mm:ss format"""
        if seconds <= 0:
            return "N/A"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def diagnose_mp3(self):
        """Diagnostic tool for MP3 files"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select MP3 File to Diagnose", "", "MP3 Files (*.mp3)"
        )
        
        if not file_path:
            return
            
        try:
            # Basic file info
            size = os.path.getsize(file_path)
            
            # Try to read header
            with open(file_path, 'rb') as f:
                header = f.read(10)
                
            # Check backends
            backends = []
            try:
                import subprocess
                subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
                backends.append("ffmpeg")
            except:
                pass
                
            try:
                import subprocess
                subprocess.check_output(['avconv', '-version'], stderr=subprocess.STDOUT)
                backends.append("avconv")
            except:
                pass
                
            # Try loading with different methods
            results = []
            
            # 1. librosa
            try:
                y, sr = librosa.load(file_path, sr=22050, mono=True, duration=5)
                results.append(f"librosa: SUCCESS ({len(y)} samples)")
            except Exception as e:
                results.append(f"librosa: FAILED ({str(e)})")
                
            # 2. pydub
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(file_path, format="mp3")
                results.append(f"pydub: SUCCESS ({len(audio)} ms, {audio.channels} channels)")
            except Exception as e:
                results.append(f"pydub: FAILED ({str(e)})")
                
            # 3. audioread
            try:
                import audioread
                with audioread.audio_open(file_path) as audio_file:
                    results.append(f"audioread: SUCCESS ({audio_file.samplerate} Hz)")
            except Exception as e:
                results.append(f"audioread: FAILED ({str(e)})")
                
            # Show results
            QMessageBox.information(
                self,
                "MP3 Diagnostic Results",
                f"File: {file_path}\n"
                f"Size: {size} bytes\n"
                f"Header: {header.hex()[:20]}...\n\n"
                f"Available backends: {', '.join(backends) if backends else 'NONE'}\n\n"
                f"Loading tests:\n" + "\n".join(results)
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Diagnostic Error",
                f"Error diagnosing MP3: {str(e)}"
            )
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ComparisonGUI()
    window.show()
    sys.exit(app.exec_())