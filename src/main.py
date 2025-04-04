import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QProgressBar, QTableWidget,
                            QTableWidgetItem, QHeaderView, QGroupBox, QButtonGroup, 
                            QRadioButton, QMessageBox, QMenu, QInputDialog, QComboBox)

from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from runner import Runner

class ComparisonGUI(QMainWindow):
    # Constant for col names
    COLUMN_NAMES = ["Remastered", "Original", "Confidence",
                   "Remaster Duration", "Original Duration"]
    # Constant for determining min confidence level before determining if a match
    CONFIDENCE_THRESHOLD = 0.4
    
    def __init__(self):
        super().__init__()

        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.img_dir = os.path.join(self.base_path, 'img')

        self.original_files = []
        self.remastered_files = []
        self.init_ui()
        self.results = []
        self.runner = None

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.rename_action = None

    def init_ui(self):
        """
        Initializes the UI.
        """
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
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Non-editable cells
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        # self.table.setFocusPolicy(Qt.NoFocus)  # Remove focus border

        # fix backslash issues and make explicit var
        arrow_up = os.path.join(self.img_dir, 'arrow_up.png').replace('\\', '/')
        arrow_down = os.path.join(self.img_dir, 'arrow_down.png').replace('\\', '/')

        # Custom table stylesheet for selection cells
        self.table.setStyleSheet(f"""
            QTableWidget::item:selected {{
                background-color: #e0e0e0;
                color: black;
            }}
            QTableCornerButton::section {{
                background-color: transparent;
                border: none;
            }}
            QHeaderView::section {{
                background-color: white;
                border: none;
                padding-right: 15px;
            }}
            QHeaderView::down-arrow {{
            image: url({arrow_down});
            width: 12px;
            height: 12px;
            }}
            QHeaderView::up-arrow {{
                image: url({arrow_up});
                width: 12px;
                height: 12px;
            }}
        """)

        # arrow existing debug 
        print("Arrow paths:")
        print("Up:", arrow_up, "Exists:", os.path.exists(arrow_up))
        print("Down:", arrow_down, "Exists:", os.path.exists(arrow_down))

        
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Original", "Remastered", "Confidence", "Original Duration", "Remastered Duration"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # sort in table
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.update_sort_indicator)

        layout.addWidget(self.table)

        # Disable header interactions
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionsClickable(True)
        
        vertical_header = self.table.verticalHeader()
        # vertical_header.setVisible(False)  # Hide row #s
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
        self.refresh_btn = QPushButton("Refresh Table")
        self.refresh_btn.clicked.connect(self.refresh_table)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.refresh_btn)
        layout.addLayout(btn_layout)
        
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    # When the source and target file cells are right clicked = context menu
    def context_menu(self, pos):
        """
        Displays a context menu for the selected cell when right clicked.
        """
        menu = QMenu()
        item = self.table.itemAt(pos)
        
        if item and item.column() in (0, 1):
            self.rename_action = menu.addAction("Rename")
            self.rename_action.triggered.connect(lambda: self.rename_file(item))
            
            self.match_action = menu.addAction("Match Name")
            self.match_action.triggered.connect(lambda: self.match_name(item))
            
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def match_name(self, item):
        """
        Matches the name of the selected cell to the name of the other.
        """
        row = item.row()
        col = item.column()
        result = self.results[row]
        
        # Check confidence threshold (fail for bad matches)
        if result['confidence'] < self.CONFIDENCE_THRESHOLD:
            QMessageBox.warning(self, "No Match", 
                            "Cannot match names for files with low confidence score")
            return
        
        # Determine source and target names
        if col == 0:  # Remastered -> Original
            source_path = result.get('orig_path', '')
            target_path = result['path']
            direction = "remastered to match original"
        elif col == 1:  # Original -> Remastered
            source_path = result['path']
            target_path = result.get('orig_path', '')
            direction = "original to match remastered"
        else:
            return
        
        if not source_path or not target_path:
            QMessageBox.warning(self, "Error", "No matching file exists")
            return
        
        # Get only base name (no extensions)
        source_base = os.path.splitext(os.path.basename(source_path))[0]
        target_base, target_ext = os.path.splitext(os.path.basename(target_path))
        
        # Confirm rename
        reply = QMessageBox.question(
            self,
            "Confirm Name Match",
            f"Are you sure you want to rename {direction}?\n"
            f"New name: {source_base}{target_ext}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            new_name = f"{source_base}{target_ext}"
            new_path = os.path.join(os.path.dirname(target_path), new_name)
            
            try:
                os.rename(target_path, new_path)
                
                # Update records
                if col == 0:
                    self.results[row]['path'] = new_path
                    self.results[row]['display_name'] = source_base
                    self.table.item(row, 0).setText(source_base)
                else:
                    self.results[row]['orig_path'] = new_path
                    # Update the comparator reference
                    if self.runner and hasattr(self.runner, 'comparator') and self.runner.comparator:
                        original_name = os.path.basename(new_path)
                        if original_name in self.runner.comparator.reference_features:
                            self.runner.comparator.reference_features[original_name]['path'] = new_path

                QMessageBox.information(self, "Success", "File name matched successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename file: {str(e)}")

    def rename_file(self, item):
        """
        Renames the file of the selected cell.

        Args:
            item (QTableWidgetItem): The file to be renamed.
        """
        row = item.row()
        col = item.column()
        
        # Get current sort state
        header = self.table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        
        # Get current file information using the table item data
        current_path = ""
        old_name = ""
        
        # Find the correct result entry based on file path from the table item
        table_item = self.table.item(row, col)
        if col == 0:  # Remastered
            current_path = table_item.data(Qt.UserRole)
            # Find the matching result entry
            result_entry = next((r for r in self.results if r['path'] == current_path), None)
            if not result_entry:
                QMessageBox.warning(self, "Error", "Couldn't find matching file data!")
                return
        elif col == 1:  # Original
            current_path = table_item.data(Qt.UserRole)
            # Find the matching result entry based on og file path
            result_entry = next((r for r in self.results if r.get('orig_path', '') == current_path), None)
            if not result_entry:
                QMessageBox.warning(self, "Error", "Couldn't find matching file data!")
                return
        
        if not current_path or not os.path.exists(current_path):
            QMessageBox.warning(self, "Error", "File not found!")
            return

        # Get new name from user
        current_base = os.path.splitext(os.path.basename(current_path))[0]
        new_name, confirm = QInputDialog.getText(
            self, "Rename File", "Enter new name:", text=current_base
        )
        
        if not new_name or not confirm:
            return

        # Validate extension
        original_ext = os.path.splitext(current_path)[1]
        new_base, new_ext = os.path.splitext(new_name)
        if not new_ext:
            new_name += original_ext
        elif new_ext.lower() != original_ext.lower():
            QMessageBox.warning(self, "Invalid Extension", 
                            f"Extension must remain {original_ext}"
                            f"\nTry including {original_ext} in the new name.")
            return

        # Create new path
        new_path = os.path.join(os.path.dirname(current_path), new_name)
        
        try:
            # File rename
            os.rename(current_path, new_path)
            
            # Update all relevant records
            if col == 0:  # Renaming remastered file
                # Update the found result entry with new path and display name
                result_entry['path'] = new_path
                result_entry['display_name'] = os.path.basename(new_path)
            else:  # Renaming original file
                new_base_name = os.path.basename(new_path)
                old_name = os.path.basename(current_path)
                
                # Update all matches across the results
                for result in self.results:
                    if result.get('orig_path', '') == current_path:
                        result['orig_path'] = new_path
                    if result['match'] == old_name:
                        result['match'] = new_base_name
                        result['orig_path'] = new_path

                # Update comparator refs
                if self.runner and self.runner.comparator:
                    comparator = self.runner.comparator
                    if old_name in comparator.reference_features:
                        # Update all ref features with new path
                        ref_data = comparator.reference_features[old_name]
                        ref_data['path'] = new_path
                        comparator.reference_features[new_base_name] = ref_data
                        del comparator.reference_features[old_name]

            # Full table refresh + sort preservation
            self._refresh_full_table(sort_col, sort_order)
            
            # Check if the rename was successful
            if not os.path.exists(new_path):
                raise Exception("File rename operation completed but file not found at new location")
            
            QMessageBox.information(self, "Success", "File renamed successfully!")

        except PermissionError:
            QMessageBox.warning(self, "File in Use", 
                            "Cannot rename file while it is being used by another process.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not rename file:\n{str(e)}")
            # Only refresh if we need to recover from an error
            if not os.path.exists(current_path) and os.path.exists(new_path):
                self.refresh_table()

    def _validate_table_integrity(self):
        """
        Helper to ensure table rows match the file data (names).
        """
        for row in range(self.table.rowCount()):
            table_name = self.table.item(row, 0).text()
            data_name = os.path.basename(self.results[row]['path'])
            if table_name != data_name:
                print(f"Mismatch at row {row}: Table '{table_name}' vs Data '{data_name}'")
                self.table.item(row, 0).setText(data_name)



    def _refresh_full_table(self, sort_col, sort_order):
        """
        Helper to complete refresh with sort preservation.
        Handles the core table refresh logic.

        Args:
            sort_col (int): The column to sort by.
            sort_order (Qt.SortOrder): The order to sort by.
        """
        # Store current selection and initialize a selected item
        selected_row = self.table.currentRow()
        selected_item = None
        if 0 <= selected_row < len(self.results):
            # Store both remastered and original paths for the selected row
            selected_item = {
                'remastered': self.results[selected_row]['path'],
                'original': self.results[selected_row].get('orig_path', ''),
                'column': self.table.currentColumn()
            }
        
        # Re-sort the data first
        self._run_sort(sort_col, sort_order)
        
        # Clear and rebuild table to refresh and stay synced
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.results))
        
        for row, result in enumerate(self.results):
            # Remastered name - uses display name
            remastered_name = result.get('display_name', os.path.basename(result['path']))
            remastered_item = QTableWidgetItem(remastered_name)
            remastered_item.setData(Qt.UserRole, result['path'])
            self.table.setItem(row, 0, remastered_item)
            
            # Original name - try to use real file name otherwise use match name
            original_name = os.path.basename(result.get('orig_path', '')) if result.get('orig_path') else result['match']
            original_item = QTableWidgetItem(original_name)
            original_item.setData(Qt.UserRole, result.get('orig_path', ''))
            self.table.setItem(row, 1, original_item)
            
            # Confidence
            conf_item = QTableWidgetItem(f"{result['confidence']:.2f}")
            conf_item.setBackground(self.confidence_color(result['confidence']))
            self.table.setItem(row, 2, conf_item)
            
            # Durations
            self.table.setItem(row, 3, QTableWidgetItem(self.format_duration(result['orig_duration'])))
            orig_duration = self.format_duration(result['rem_duration']) if result['rem_duration'] > 0 else "N/A"
            self.table.setItem(row, 4, QTableWidgetItem(orig_duration))

        # Restore selection based on file path
        if selected_item:
            path_to_find = selected_item['remastered'] if selected_item['column'] == 0 else selected_item['original']
            column_to_check = 0 if selected_item['column'] == 0 else 1
            
            for row in range(self.table.rowCount()):
                if self.table.item(row, column_to_check).data(Qt.UserRole) == path_to_find:
                    self.table.setCurrentCell(row, selected_item['column'])
                    break

        # Apply visual sort indicators
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicator(sort_col, sort_order)
        self.table.sortByColumn(sort_col, sort_order)
        
        # Force immediate UI update
        self.table.viewport().update()
        
        # Validate table integrity after refresh
        self._validate_table_integrity()

    def refresh_table(self):
        """
        Forces a complete table refresh while maintaining current sort order.
        Handles the file system changes and user interaction when using refresh.
        """

        # Store current sort state
        header = self.table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()

        # Track which directories we need to scan
        dirs_to_scan = set()
        missing_files = []
        
        # First pass: identify missing files and directories to scan
        for result in self.results:
            if not os.path.exists(result['path']):
                dirs_to_scan.add(os.path.dirname(result['path']))
                missing_files.append(('remastered', result))


            if result.get('orig_path') and not os.path.exists(result['orig_path']):
                dirs_to_scan.add(os.path.dirname(result['orig_path']))
                missing_files.append(('original', result))

        if not missing_files:
            # No files to update, just refresh the display
            self._refresh_full_table(sort_col, sort_order)
            QMessageBox.information(self, "Refresh Complete", 
                                "Table has been refreshed with current file states.")
            return

        # Scan directories and build file size map to associate with unlocated files
        updated_files = False
        for dir_path in dirs_to_scan:
            # Map of file sizes to paths for the directory
            size_map = {}
            for file in os.listdir(dir_path):
                if file.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):
                    try:
                        file_path = os.path.join(dir_path, file)
                        size_map[os.path.getsize(file_path)] = file_path
                    except:
                        continue

            # Check each missing file against the size map
            for file_type, result in missing_files:
                if file_type == 'remastered' and 'file_size' in result:
                    if result['file_size'] in size_map:
                        new_path = size_map[result['file_size']]
                        result['path'] = new_path
                        result['display_name'] = os.path.basename(new_path)
                        updated_files = True
                elif file_type == 'original' and 'orig_file_size' in result:
                    if result['orig_file_size'] in size_map:
                        new_path = size_map[result['orig_file_size']]
                        result['orig_path'] = new_path
                        result['match'] = os.path.splitext(os.path.basename(new_path))[0]
                        updated_files = True

        # Refresh the table with updated paths
        self._refresh_full_table(sort_col, sort_order)

        # Show appropriate message
        if updated_files:
            QMessageBox.information(self, "Refresh Complete", 
                                "Table has been refreshed and updated with renamed files.")
        else:
            QMessageBox.information(self, "Refresh Complete", 
                                "Table has been refreshed with current file states.")

    def _run_sort(self, col, order):
        """
        Helper to sort the underlying results list using proper keys to
        ensure table displays the correct, current data.

        Args: 
            col (int): The column to sort by.
            order (Qt.SortOrder): The order to sort by (ascending or descending).
        """
        reverse = order == Qt.DescendingOrder
        
        if col == 0:  # Original
            self.results.sort(key=lambda x: os.path.basename(x.get('orig_path', '')), reverse=reverse)
        elif col == 1:  # Remastered
            self.results.sort(key=lambda x: os.path.basename(x['path']), reverse=reverse)
        elif col == 2:  # Confidence
            self.results.sort(key=lambda x: x['confidence'], reverse=reverse)
        elif col == 3:  # Original Duration
            self.results.sort(key=lambda x: x['orig_duration'], reverse=reverse)
        elif col == 4:  # Remastered Duration
            self.results.sort(key=lambda x: x['rem_duration'], reverse=reverse)

    def select_files(self, is_original=True):
        """
        Selects files from selected files/folders to be used for comparison.
        Args:
            is_original (bool, Default = True): If True, select original files. If False, select remastered files.
        """
        file_type = "Original" if is_original else "Remastered"
        target_files = self.original_files if is_original else self.remastered_files
        target_label = self.orig_label if is_original else self.remastered_label
        
        if self.folder_rb.isChecked():
            path = QFileDialog.getExistingDirectory(self, f"Select {file_type} Folder")
            if path:
                target_files = self.scan_audio_files(path)
                target_label.setText(f"{file_type} Files: {len(target_files)} in folder")
                # Verify if any audio files found
                if not target_files:
                    QMessageBox.warning(self, "Warning", 
                                    f"No audio files found in {path}.\n"
                                    "Check that the folder contains supported audio files.")
        else:
            files, _ = QFileDialog.getOpenFileNames(
                self, 
                f"Select {file_type} Files", 
                "", 
                "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a)"
            )
            if files:
                # Verify each file exists
                valid_files = [f for f in files if os.path.exists(f)]
                if len(valid_files) != len(files):
                    QMessageBox.warning(self, "Warning", 
                                    f"{len(files) - len(valid_files)} files could not be accessed.")
                
                target_files = valid_files
                target_label.setText(f"{file_type} Files: {len(valid_files)} selected")
        
        # Update the class variable
        if is_original:
            self.original_files = target_files
        else:
            self.remastered_files = target_files

    def select_originals(self):
        """
        Selects the original files from selected files/folders.
        """
        self.select_files(is_original=True)

    def select_remastered(self):
        """
        Selects the remastered files from selected files/folders.
        """
        self.select_files(is_original=False)

    def scan_audio_files(self, folder):
        """
        Scans the audio files in the selected folder.

        Returns:
            list: A list of audio files from the selected folder.
        """
        audio_files = []
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):
                    audio_files.append(os.path.join(root, file))
        return audio_files
    
    def start_comparison(self):
        """
        Starts the process for comparing the files.
        """
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
        self.refresh_btn.setEnabled(False)
        
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
        """
        Updates the progress bar and status label.

        Args:
            value (int): The value to set the progress bar to.
            message (str): The message to display in the status label.
        """
        self.progress.setValue(value)
        self.status_label.setText(message)

    def show_error(self, error_msg):
        """
        Shows error message and stops the runner.

        Args: 
            error_msg (str): The error message to display.
        """
        QMessageBox.critical(self, "Error", error_msg)
        if self.runner:
            self.runner.stop()

    def on_runner_finished(self):
        """
        Re-enables UI once runner is finished and resets runner.
        """
        # Re-enable UI
        self.start_btn.setEnabled(True)
        self.orig_btn.setEnabled(True)
        self.remastered_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.runner = None

    def show_results(self, results):
        """
        Show the results of the comparison in the table.

        Args: 
            results (list): The results of the comparison.
        """
        # Store results and initialize table
        self.results = results.copy()
        self.table.setRowCount(len(self.results))
        
        # Temporarily disable sorting to populate data
        self.table.setSortingEnabled(False)
        
        # Populate table data
        for row, result in enumerate(self.results):
            # Store file sizes for both original and remastered files
            if result.get('orig_path') and os.path.exists(result['orig_path']):
                result['orig_file_size'] = os.path.getsize(result['orig_path'])
            if os.path.exists(result['path']):
                result['file_size'] = os.path.getsize(result['path'])
            
            # Original name with file path reference
            original_name = os.path.basename(result.get('orig_path', '')) if result.get('orig_path') else result['match']
            original_item = QTableWidgetItem(original_name)
            original_item.setData(Qt.UserRole, result.get('orig_path', ''))
            self.table.setItem(row, 0, original_item)
            
            # Remastered match with file path reference
            remastered_name = result.get('display_name', os.path.basename(result['path']))
            remastered_item = QTableWidgetItem(remastered_name)
            remastered_item.setData(Qt.UserRole, result['path'])
            self.table.setItem(row, 1, remastered_item)
            
            # Confidence with color coding
            conf_item = QTableWidgetItem(f"{result['confidence']:.2f}")
            conf_item.setBackground(self.confidence_color(result['confidence']))
            self.table.setItem(row, 2, conf_item)
            
            # Durations
            orig_duration = self.format_duration(result['orig_duration']) if result['orig_duration'] > 0 else "N/A"
            self.table.setItem(row, 3, QTableWidgetItem(orig_duration))
            self.table.setItem(row, 4, QTableWidgetItem(self.format_duration(result['rem_duration'])))

        # Re-enable sorting
        self.table.setSortingEnabled(True)
        
        # Set default sort by Original (column 0) ascending
        self.table.horizontalHeader().setSortIndicator(0, Qt.AscendingOrder)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        
        # Connect interaction signals
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.cellClicked.connect(self.on_cell_clicked)
        
        # Update status
        match_count = len([r for r in self.results if r['confidence'] > self.CONFIDENCE_THRESHOLD])
        self.status_label.setText(f"Found {match_count} matches out of {len(results)} files")

    def update_sort_indicator(self, index, order):
        """
        Handles column sorting and updates the table display with refreshed, sorted data.

        Args:
            index (int): The index of the column to sort by.
            order (Qt.SortOrder): The order to sort by (ascending or descending).
        """
        # Run the sort
        self._run_sort(index, order)

        # Get current selection before refresh
        current_item = self.table.currentItem()
        current_path = None
        if current_item and current_item.column() in (0, 1):
            current_path = current_item.data(Qt.UserRole)

        # Update the table display
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        
        # Store the sorted results order
        sorted_results = self.results.copy()
        
        for row, result in enumerate(sorted_results):
            # Update remastered col
            remastered_name = result.get('display_name', os.path.basename(result['path']))
            remastered_item = QTableWidgetItem(remastered_name)
            remastered_item.setData(Qt.UserRole, result['path'])
            self.table.setItem(row, 0, remastered_item)
            
            # Update original col
            original_name = os.path.basename(result.get('orig_path', '')) if result.get('orig_path') else result['match']
            original_item = QTableWidgetItem(original_name)
            original_item.setData(Qt.UserRole, result.get('orig_path', ''))
            self.table.setItem(row, 1, original_item)
            
            # Update confidence col
            conf_item = QTableWidgetItem(f"{result['confidence']:.2f}")
            conf_item.setBackground(self.confidence_color(result['confidence']))
            self.table.setItem(row, 2, conf_item)
            
            # Update durations cols
            self.table.setItem(row, 3, QTableWidgetItem(self.format_duration(result['orig_duration'])))
            orig_duration = self.format_duration(result['rem_duration']) if result['rem_duration'] > 0 else "N/A"
            self.table.setItem(row, 4, QTableWidgetItem(orig_duration))

        # Update the results list to match the new sort order
        self.results = sorted_results

        # Restore selection if we had one
        if current_path:
            for row in range(self.table.rowCount()):
                for col in (0, 1):
                    item = self.table.item(row, col)
                    if item and item.data(Qt.UserRole) == current_path:
                        self.table.setCurrentCell(row, col)
                        break
        
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicator(index, order)
        self.table.blockSignals(False)
        
        # Force an immediate UI update
        self.table.viewport().update()

    def on_cell_clicked(self, row, col):
        """
        Handles single clicks for highlighting the clicked cell.

        Args:
            row (int): The row of the clicked cell.
            col (int): The column of the clicked cell.
        """
        if col in (0, 1):
            self.table.clearSelection()
            item = self.table.item(row, col)
            if item:
                item.setSelected(True)
        else:
            self.table.clearSelection()

    def on_cell_double_clicked(self, row, col):
        """
        Handles double clicks for opening the file in the cell that was clicked.
        """
        if col in (0, 1):
            item = self.table.item(row, col)
            if not item:
                return
                
            file_path = item.data(Qt.UserRole)
            if not file_path:
                return
                
            try:
                if os.path.exists(file_path):
                    self.open_file(file_path)
                else:
                    # Show error with refresh option if there are issues
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setWindowTitle("File Not Found")
                    msg.setText(f"The file could not be found:\n{file_path}")
                    msg.setInformativeText("This can happen if files were renamed or moved. Try refreshing the table.")
                    
                    # Add buttons
                    refresh_btn = msg.addButton("Refresh Table", QMessageBox.ActionRole)
                    msg.addButton(QMessageBox.Ok)
                    
                    response = msg.exec_()
                    
                    if response == 0:  # Refresh Table button is clicked
                        self.refresh_table()
                            
            except Exception as e:
                QMessageBox.critical(self, "Open Error",
                                f"Could not open file:\n{file_path}\nError: {str(e)}")

    @staticmethod
    def open_file(path):
        """
        Opens (audio) file with user's default application.
        """
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
        """
        Convert seconds to mm:ss format.

        Args:
            seconds (int): The number of seconds to convert.

        Returns:
            str: The duration in mm:ss format.
        """
        if seconds <= 0:
            return "N/A"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ComparisonGUI()
    window.show()
    sys.exit(app.exec_())