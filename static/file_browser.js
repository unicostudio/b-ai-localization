/**
 * File browser functionality for the localization tool web interface
 */

class FileBrowser {
    constructor(modalId, inputId, btnId, isFolderMode = true, fileType = null) {
        this.modalId = modalId;
        this.inputId = inputId;
        this.btnId = btnId;
        this.isFolderMode = isFolderMode;
        this.fileType = fileType;
        this.currentPath = '';
        this.modal = null;
        this.selectedPath = '';
        
        this.init();
    }
    
    init() {
        // Create modal dialog for file/folder browser if it doesn't exist
        if (!document.getElementById(this.modalId)) {
            this.createModal();
        }
        
        // Initialize the modal
        this.modal = new bootstrap.Modal(document.getElementById(this.modalId));
        
        // Add event listener to the browse button
        document.getElementById(this.btnId).addEventListener('click', () => {
            this.openBrowser();
        });
        
        // Add event listener to the select button
        document.getElementById(`${this.modalId}-select`).addEventListener('click', () => {
            this.selectPath();
        });
    }
    
    createModal() {
        const modalType = this.isFolderMode ? 'folder' : 'file';
        const modalTitle = this.isFolderMode ? 'Select Folder' : `Select ${this.fileType.toUpperCase()} File`;
        
        const modalHtml = `
        <div class="modal fade" id="${this.modalId}" tabindex="-1" aria-labelledby="${this.modalId}-label" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${this.modalId}-label">${modalTitle}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <div class="input-group">
                                <input type="text" class="form-control" id="${this.modalId}-path" readonly>
                                <button class="btn btn-outline-secondary" type="button" id="${this.modalId}-parent">⬆️ Up</button>
                            </div>
                        </div>
                        <div class="list-group" id="${this.modalId}-items" style="max-height: 300px; overflow-y: auto;">
                            <!-- Items will be loaded dynamically -->
                            <div class="text-center p-3">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="${this.modalId}-select">Select ${modalType}</button>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Add modal to the document
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Add event listener for parent directory button
        document.getElementById(`${this.modalId}-parent`).addEventListener('click', () => {
            if (this.currentPath) {
                const url = this.isFolderMode 
                    ? `/browse_directory?path=${encodeURIComponent(this.parentPath)}`
                    : `/browse_files?path=${encodeURIComponent(this.parentPath)}&file_type=${this.fileType}`;
                
                this.loadItems(url);
            }
        });
    }
    
    openBrowser() {
        // Show the modal
        this.modal.show();
        
        // Load initial items
        const initialPath = document.getElementById(this.inputId).value || '/';
        const url = this.isFolderMode 
            ? `/browse_directory?path=${encodeURIComponent(initialPath)}`
            : `/browse_files?path=${encodeURIComponent(initialPath)}&file_type=${this.fileType}`;
        
        this.loadItems(url);
    }
    
    loadItems(url) {
        const itemsContainer = document.getElementById(`${this.modalId}-items`);
        itemsContainer.innerHTML = `
            <div class="text-center p-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                this.currentPath = data.current_path;
                this.parentPath = data.parent_dir;
                
                // Update path display
                document.getElementById(`${this.modalId}-path`).value = this.currentPath;
                
                // Clear items container
                itemsContainer.innerHTML = '';
                
                // Add each item to the list
                if (data.items.length === 0) {
                    itemsContainer.innerHTML = '<div class="list-group-item text-center">No items found</div>';
                } else {
                    data.items.forEach(item => {
                        const icon = item.is_dir ? '📁' : (this.isFolderMode ? '📄' : '📄');
                        const itemClass = !this.isFolderMode && !item.is_dir ? 'selectable-file' : '';
                        const itemElement = document.createElement('a');
                        itemElement.href = '#';
                        itemElement.className = `list-group-item list-group-item-action ${itemClass}`;
                        itemElement.innerHTML = `${icon} ${item.name}`;
                        itemElement.dataset.path = item.path;
                        itemElement.dataset.isDir = item.is_dir;
                        
                        itemElement.addEventListener('click', (e) => {
                            e.preventDefault();
                            
                            if (item.is_dir) {
                                // Navigate to the directory
                                const url = this.isFolderMode 
                                    ? `/browse_directory?path=${encodeURIComponent(item.path)}`
                                    : `/browse_files?path=${encodeURIComponent(item.path)}&file_type=${this.fileType}`;
                                
                                this.loadItems(url);
                            } else if (!this.isFolderMode) {
                                // Select the file
                                this.selectedPath = item.path;
                                
                                // Highlight the selected file
                                const items = itemsContainer.querySelectorAll('.selectable-file');
                                items.forEach(i => i.classList.remove('active'));
                                itemElement.classList.add('active');
                            }
                        });
                        
                        itemsContainer.appendChild(itemElement);
                    });
                }
                
                // For folder mode, update the selected path
                if (this.isFolderMode) {
                    this.selectedPath = this.currentPath;
                }
            })
            .catch(error => {
                itemsContainer.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            });
    }
    
    selectPath() {
        // Update the input field with the selected path
        document.getElementById(this.inputId).value = this.selectedPath;
        
        // Close the modal
        this.modal.hide();
    }
}

// Initialize after page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize directory browser for images directory
    const imagesDirBrowser = new FileBrowser('images-dir-modal', 'images_dir', 'browse-images-dir');
    
    // Initialize file browser for characters JSON file
    const charsFileBrowser = new FileBrowser('chars-file-modal', 'chars_file', 'browse-chars-file', false, 'json');
});
