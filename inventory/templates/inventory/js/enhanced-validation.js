/**
 * Enhanced form validation and user experience script
 * Used for optimizing mobile responsiveness, form validation, batch operations, and security mechanisms
 */

document.addEventListener('DOMContentLoaded', function() {
    // Enhance form validation
    enhanceFormValidation();
    
    // Optimize mobile table and form layout
    enhanceMobileResponsiveness();
    
    // Add batch operations functionality
    setupBatchOperations();
    
    // Enhance password policy and secondary confirmation mechanism
    enhanceSecurityFeatures();
});

/**
 * Enhance form validation functionality
 */
function enhanceFormValidation() {
    // Get all forms that need validation
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Add validation class to all forms
        form.classList.add('needs-validation');
        
        // Add visual indicators for required fields
        form.querySelectorAll('[required]').forEach(field => {
            // Get field label
            const label = form.querySelector(`label[for="${field.id}"]`);
            if (label && !label.querySelector('.required-indicator')) {
                const indicator = document.createElement('span');
                indicator.className = 'required-indicator text-danger ms-1';
                indicator.textContent = '*';
                label.appendChild(indicator);
            }
            
            // Add real-time validation feedback
            field.addEventListener('input', function() {
                validateField(this);
            });
            
            field.addEventListener('blur', function() {
                validateField(this, true);
            });
        });
        
        // Validate before form submission
        form.addEventListener('submit', function(event) {
            let isValid = true;
            
            // Validate all required fields
            form.querySelectorAll('[required]').forEach(field => {
                if (!validateField(field, true)) {
                    isValid = false;
                }
            });
            
            // Validate password field
            const passwordField = form.querySelector('input[type="password"]');
            if (passwordField && passwordField.value && !validatePassword(passwordField.value)) {
                isValid = false;
                showValidationError(passwordField, 'Password must contain at least 8 characters, including uppercase and lowercase letters, numbers, and special characters');
            }
            
            // If validation fails, prevent form submission
            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();
                
                // Scroll to first invalid field
                const firstInvalidField = form.querySelector('.is-invalid');
                if (firstInvalidField) {
                    firstInvalidField.focus();
                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    });
}

/**
 * Validate a single field
 * @param {HTMLElement} field - Form field to validate
 * @param {boolean} showError - Whether to show error message
 * @returns {boolean} - Whether validation passed
 */
function validateField(field, showError = false) {
    let isValid = field.checkValidity();
    
    // Special field validation
    if (field.type === 'email' && field.value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        isValid = emailRegex.test(field.value);
        if (!isValid && showError) {
            showValidationError(field, 'Please enter a valid email address');
        }
    } else if (field.type === 'tel' && field.value) {
        const phoneRegex = /^1[3-9]\d{9}$/;
        isValid = phoneRegex.test(field.value);
        if (!isValid && showError) {
            showValidationError(field, 'Please enter a valid phone number');
        }
    } else if (field.name === 'barcode' && field.value) {
        // Barcode validation logic
        const barcodeRegex = /^[A-Za-z0-9\-]{4,}$/;
        isValid = barcodeRegex.test(field.value);
        if (!isValid && showError) {
            showValidationError(field, 'Barcode format is incorrect, please check');
        }
    }
    
    // Show or hide validation feedback
    if (showError) {
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            
            // Remove existing error message
            const errorElement = field.nextElementSibling;
            if (errorElement && errorElement.classList.contains('invalid-feedback')) {
                errorElement.remove();
            }
        } else if (!field.classList.contains('is-invalid')) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            
            // If no custom error message, add default message
            if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('invalid-feedback')) {
                showValidationError(field, 'This field is required');
            }
        }
    }
    
    return isValid;
}

/**
 * Show validation error message
 * @param {HTMLElement} field - Form field
 * @param {string} message - Error message
 */
function showValidationError(field, message) {
    // Remove existing error message
    const existingError = field.nextElementSibling;
    if (existingError && existingError.classList.contains('invalid-feedback')) {
        existingError.remove();
    }
    
    // Create new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    // Insert error message
    field.parentNode.insertBefore(errorDiv, field.nextSibling);
}

/**
 * Validate password strength
 * @param {string} password - Password
 * @returns {boolean} - Whether password meets requirements
 */
function validatePassword(password) {
    // Password must be at least 8 characters, including uppercase and lowercase letters, numbers, and special characters
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$/;
    return passwordRegex.test(password);
}

/**
 * Optimize mobile table and form layout
 */
function enhanceMobileResponsiveness() {
    // Optimize table display on mobile devices
    const tables = document.querySelectorAll('.table-responsive table');
    tables.forEach(table => {
        // Add horizontal scroll hint for table
        const tableContainer = table.closest('.table-responsive');
        if (tableContainer && !tableContainer.querySelector('.swipe-hint')) {
            const hint = document.createElement('div');
            hint.className = 'swipe-hint d-md-none text-muted small mb-2';
            hint.innerHTML = '<i class="bi bi-arrow-left-right me-1"></i>Swipe left/right to see more';
            tableContainer.insertBefore(hint, table);
        }
        
        // Add touch feedback for table rows
        table.querySelectorAll('tbody tr').forEach(row => {
            row.addEventListener('touchstart', function() {
                this.classList.add('active-touch');
            }, { passive: true });
            
            row.addEventListener('touchend', function() {
                this.classList.remove('active-touch');
            }, { passive: true });
        });
    });
    
    // Optimize form layout on mobile devices
    const formGroups = document.querySelectorAll('.form-group, .mb-3');
    formGroups.forEach(group => {
        // Ensure labels and inputs stack vertically on small screens
        const label = group.querySelector('label');
        const input = group.querySelector('input, select, textarea');
        
        if (label && input) {
            label.classList.add('d-block');
            input.classList.add('w-100');
        }
    });
    
    // Optimize dropdown select display on mobile
    document.querySelectorAll('select').forEach(select => {
        select.addEventListener('focus', function() {
            if (window.innerWidth < 768) {
                // On mobile devices, ensure dropdown is not truncated
                this.style.maxHeight = '38px';
            }
        });
    });
}

/**
 * Setup batch operations functionality
 */
function setupBatchOperations() {
    // Add batch selection functionality
    setupBatchSelection();
    
    // Add batch operation buttons
    setupBatchActionButtons();
}

/**
 * Setup batch selection functionality
 */
function setupBatchSelection() {
    // Find all tables
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
        // Check if table already has selection column
        const hasCheckboxColumn = table.querySelector('thead th.select-column');
        if (!hasCheckboxColumn) {
            // Add header selection column
            const headerRow = table.querySelector('thead tr');
            if (headerRow) {
                const selectAllHeader = document.createElement('th');
                selectAllHeader.className = 'select-column';
                selectAllHeader.style.width = '40px';
                
                const selectAllCheckbox = document.createElement('input');
                selectAllCheckbox.type = 'checkbox';
                selectAllCheckbox.className = 'form-check-input select-all';
                selectAllCheckbox.setAttribute('aria-label', 'Select all rows');
                
                selectAllHeader.appendChild(selectAllCheckbox);
                headerRow.insertBefore(selectAllHeader, headerRow.firstChild);
                
                // Add checkbox for each row
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const selectCell = document.createElement('td');
                    selectCell.className = 'select-column';
                    
                    const rowCheckbox = document.createElement('input');
                    rowCheckbox.type = 'checkbox';
                    rowCheckbox.className = 'form-check-input select-row';
                    rowCheckbox.setAttribute('aria-label', 'Select this row');
                    
                    selectCell.appendChild(rowCheckbox);
                    row.insertBefore(selectCell, row.firstChild);
                });
                
                // Add select all/deselect all functionality
                selectAllCheckbox.addEventListener('change', function() {
                    const isChecked = this.checked;
                    table.querySelectorAll('.select-row').forEach(checkbox => {
                        checkbox.checked = isChecked;
                    });
                    
                    // Update batch operation button status
                    updateBatchActionButtons();
                });
                
                // Add row selection event
                table.querySelectorAll('.select-row').forEach(checkbox => {
                    checkbox.addEventListener('change', function() {
                        updateBatchActionButtons();
                        
                        // Update select all checkbox status
                        const allCheckboxes = table.querySelectorAll('.select-row');
                        const checkedCheckboxes = table.querySelectorAll('.select-row:checked');
                        selectAllCheckbox.checked = allCheckboxes.length === checkedCheckboxes.length;
                        selectAllCheckbox.indeterminate = checkedCheckboxes.length > 0 && checkedCheckboxes.length < allCheckboxes.length;
                    });
                });
            }
        }
    });
}

/**
 * Setup batch action buttons
 */
function setupBatchActionButtons() {
    // Find containers where batch action buttons can be added
    const actionContainers = document.querySelectorAll('.card-body .d-flex.flex-wrap.gap-2');
    
    actionContainers.forEach(container => {
        // Check if batch action button group already exists
        if (!container.querySelector('.batch-actions')) {
            // Create batch action button group
            const batchActionsDiv = document.createElement('div');
            batchActionsDiv.className = 'batch-actions dropdown d-none ms-2';
            
            // Create dropdown menu button
            const dropdownButton = document.createElement('button');
            dropdownButton.className = 'btn btn-outline-primary dropdown-toggle';
            dropdownButton.type = 'button';
            dropdownButton.setAttribute('data-bs-toggle', 'dropdown');
            dropdownButton.setAttribute('aria-expanded', 'false');
            dropdownButton.innerHTML = '<i class="bi bi-list-check me-1"></i> Batch Actions <span class="badge bg-primary ms-1 selected-count">0</span>';
            
            // Create dropdown menu
            const dropdownMenu = document.createElement('ul');
            dropdownMenu.className = 'dropdown-menu';
            
            // Add batch operation options
            const actions = [
                { text: 'Batch Export', icon: 'bi-download', action: 'exportSelected' },
                { text: 'Batch Delete', icon: 'bi-trash', action: 'deleteSelected', class: 'text-danger' }
            ];
            
            // Add specific operations based on page type
            if (window.location.pathname.includes('/product/')) {
                actions.splice(1, 0, { text: 'Batch Adjust Price', icon: 'bi-currency-yen', action: 'adjustPrice' });
            } else if (window.location.pathname.includes('/inventory/')) {
                actions.splice(1, 0, { text: 'Batch Adjust Stock', icon: 'bi-box-seam', action: 'adjustStock' });
            }
            
            // Create menu items
            actions.forEach(action => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.className = `dropdown-item batch-action ${action.class || ''}`;
                a.href = '#';
                a.setAttribute('data-action', action.action);
                a.innerHTML = `<i class="bi ${action.icon} me-2"></i>${action.text}`;
                
                li.appendChild(a);
                dropdownMenu.appendChild(li);
                
                // Add event listener
                a.addEventListener('click', function(e) {
                    e.preventDefault();
                    handleBatchAction(this.getAttribute('data-action'));
                });
            });
            
            // Assemble dropdown menu
            batchActionsDiv.appendChild(dropdownButton);
            batchActionsDiv.appendChild(dropdownMenu);
            
            // Add to container
            container.appendChild(batchActionsDiv);
        }
    });
    
    // Initialize batch action button status
    updateBatchActionButtons();
}

/**
 * Update batch action button status
 */
function updateBatchActionButtons() {
    const selectedRows = document.querySelectorAll('.select-row:checked');
    const batchActions = document.querySelectorAll('.batch-actions');
    
    batchActions.forEach(actionDiv => {
        if (selectedRows.length > 0) {
            actionDiv.classList.remove('d-none');
            actionDiv.querySelector('.selected-count').textContent = selectedRows.length;
        } else {
            actionDiv.classList.add('d-none');
        }
    });
}

/**
 * Handle batch operations
 * @param {string} action - Operation type
 */
function handleBatchAction(action) {
    // Get selected rows
    const selectedRows = document.querySelectorAll('.select-row:checked');
    const selectedIds = Array.from(selectedRows).map(checkbox => {
        const row = checkbox.closest('tr');
        return row.getAttribute('data-id') || '';
    }).filter(id => id);
    
    if (selectedIds.length === 0) {
        showAlert('Please select items to operate on first', 'warning');
        return;
    }
    
    switch (action) {
        case 'exportSelected':
            exportSelectedItems(selectedIds);
            break;
        case 'deleteSelected':
            confirmDeleteSelected(selectedIds);
            break;
        case 'adjustPrice':
            showAdjustPriceModal(selectedIds);
            break;
        case 'adjustStock':
            showAdjustStockModal(selectedIds);
            break;
        default:
            console.warn('Unknown batch operation:', action);
    }
}

/**
 * Export selected items
 * @param {Array} ids - IDs of selected items
 */
function exportSelectedItems(ids) {
    // Create a form to submit export request
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'export/';
    form.style.display = 'none';
    
    // Add CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // Add selected IDs
    ids.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    // Submit form
    document.body.appendChild(form);
    form.submit();
}

/**
 * Confirm delete selected items
 * @param {Array} ids - IDs of selected items
 */
function confirmDeleteSelected(ids) {
    Swal.fire({
        title: 'Confirm Delete',
        text: `Are you sure you want to delete the selected ${ids.length} item(s)? This operation cannot be undone!`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Confirm Delete',
        cancelButtonText: 'Cancel',
        focusCancel: true
    }).then((result) => {
        if (result.isConfirmed) {
            // Execute delete operation
            deleteSelectedItems(ids);
        }
    });
}

/**
 * Delete selected items
 * @param {Array} ids - IDs of selected items
 */
function deleteSelectedItems(ids) {
    // Create a form to submit delete request
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'batch-delete/';
    form.style.display = 'none';
    
    // Add CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // Add selected IDs
    ids.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    // Submit form
    document.body.appendChild(form);
    form.submit();
}

/**
 * Show adjust price modal
 * @param {Array} ids - IDs of selected items
 */
function showAdjustPriceModal(ids) {
    // Create modal HTML
    const modalHtml = `
    <div class="modal fade" id="adjustPriceModal" tabindex="-1" aria-labelledby="adjustPriceModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="adjustPriceModalLabel">Batch Adjust Price</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="adjustPriceForm">
                        <div class="mb-3">
                            <label for="adjustmentType" class="form-label">Adjustment Method</label>
                            <select class="form-select" id="adjustmentType" required>
                                <option value="percentage">Adjust by Percentage</option>
                                <option value="fixed">Adjust by Fixed Amount</option>
                                <option value="set">Set to Specified Amount</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="adjustmentValue" class="form-label">Adjustment Value</label>
                            <div class="input-group">
                                <input type="number" class="form-control" id="adjustmentValue" step="0.01" required>
                                <span class="input-group-text adjustment-unit">%</span>
                            </div>
                            <div class="form-text">Positive values increase, negative values decrease</div>
                        </div>
                        <div class="mb-3">
                            <label for="adjustField" class="form-label">Adjustment Field</label>
                            <select class="form-select" id="adjustField" required>
                                <option value="price">Selling Price</option>
                                <option value="cost">Cost Price</option>
                                <option value="both">Selling Price and Cost Price</option>
                            </select>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="confirmAdjustPrice">Confirm Adjustment</button>
                </div>
            </div>
        </div>
    </div>
    `;
    
    // Add modal to page
    if (!document.getElementById('adjustPriceModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // Get modal element
    const modal = document.getElementById('adjustPriceModal');
    const bsModal = new bootstrap.Modal(modal);
    
    // Update adjustment unit display
    const adjustmentType = document.getElementById('adjustmentType');
    const adjustmentUnit = document.querySelector('.adjustment-unit');
    
    adjustmentType.addEventListener('change', function() {
        adjustmentUnit.textContent = this.value === 'percentage' ? '%' : '¥';
    });
    
    // Confirm button click event
    document.getElementById('confirmAdjustPrice').addEventListener('click', function() {
        const form = document.getElementById('adjustPriceForm');
        if (form.checkValidity()) {
            const type = document.getElementById('adjustmentType').value;
            const value = document.getElementById('adjustmentValue').value;
            const field = document.getElementById('adjustField').value;
            
            // Submit adjustment request
            submitPriceAdjustment(ids, type, value, field);
            bsModal.hide();
        } else {
            form.classList.add('was-validated');
        }
    });
    
    // Show modal
    bsModal.show();
}

/**
 * Submit price adjustment request
 * @param {Array} ids - IDs of selected items
 * @param {string} type - Adjustment type
 * @param {number} value - Adjustment value
 * @param {string} field - Adjustment field
 */
function submitPriceAdjustment(ids, type, value, field) {
    // Create a form to submit adjustment request
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'batch-adjust-price/';
    form.style.display = 'none';
    
    // Add CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // Add adjustment parameters
    const typeInput = document.createElement('input');
    typeInput.type = 'hidden';
    typeInput.name = 'adjustment_type';
    typeInput.value = type;
    form.appendChild(typeInput);
    
    const valueInput = document.createElement('input');
    valueInput.type = 'hidden';
    valueInput.name = 'adjustment_value';
    valueInput.value = value;
    form.appendChild(valueInput);
    
    const fieldInput = document.createElement('input');
    fieldInput.type = 'hidden';
    fieldInput.name = 'adjustment_field';
    fieldInput.value = field;
    form.appendChild(fieldInput);
    
    // Add selected IDs
    ids.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    // Submit form
    document.body.appendChild(form);
    form.submit();
}

/**
 * Show adjust stock modal
 * @param {Array} ids - IDs of selected items
 */
function showAdjustStockModal(ids) {
    // Create modal HTML
    const modalHtml = `
    <div class="modal fade" id="adjustStockModal" tabindex="-1" aria-labelledby="adjustStockModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="adjustStockModalLabel">Batch Adjust Stock</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="adjustStockForm">
                        <div class="mb-3">
                            <label for="stockAdjustmentType" class="form-label">Adjustment Method</label>
                            <select class="form-select" id="stockAdjustmentType" required>
                                <option value="add">Increase Stock</option>
                                <option value="subtract">Decrease Stock</option>
                                <option value="set">Set to Specified Quantity</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="stockAdjustmentValue" class="form-label">Adjustment Quantity</label>
                            <input type="number" class="form-control" id="stockAdjustmentValue" min="0" step="1" required>
                        </div>
                        <div class="mb-3">
                            <label for="stockAdjustmentNotes" class="form-label">Adjustment Reason</label>
                            <textarea class="form-control" id="stockAdjustmentNotes" rows="3" required></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="confirmAdjustStock">Confirm Adjustment</button>
                </div>
            </div>
        </div>
    </div>
    `;
    
    // Add modal to page
    if (!document.getElementById('adjustStockModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // Get modal element
    const modal = document.getElementById('adjustStockModal');
    const bsModal = new bootstrap.Modal(modal);
    
    // Confirm button click event
    document.getElementById('confirmAdjustStock').addEventListener('click', function() {
        const form = document.getElementById('adjustStockForm');
        if (form.checkValidity()) {
            const type = document.getElementById('stockAdjustmentType').value;
            const value = document.getElementById('stockAdjustmentValue').value;
            const notes = document.getElementById('stockAdjustmentNotes').value;
            
            // Submit adjustment request
            submitStockAdjustment(ids, type, value, notes);
            bsModal.hide();
        } else {
            form.classList.add('was-validated');
        }
    });
    
    // Show modal
    bsModal.show();
}

/**
 * Submit stock adjustment request
 * @param {Array} ids - IDs of selected items
 * @param {string} type - Adjustment type
 * @param {number} value - Adjustment value
 * @param {string} notes - Adjustment reason
 */
function submitStockAdjustment(ids, type, value, notes) {
    // Create a form to submit adjustment request
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.location.pathname + 'batch-adjust-stock/';
    form.style.display = 'none';
    
    // Add CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // Add adjustment parameters
    const typeInput = document.createElement('input');
    typeInput.type = 'hidden';
    typeInput.name = 'adjustment_type';
    typeInput.value = type;
    form.appendChild(typeInput);
    
    const valueInput = document.createElement('input');
    valueInput.type = 'hidden';
    valueInput.name = 'adjustment_value';
    valueInput.value = value;
    form.appendChild(valueInput);
    
    const notesInput = document.createElement('input');
    notesInput.type = 'hidden';
    notesInput.name = 'adjustment_notes';
    notesInput.value = notes;
    form.appendChild(notesInput);
    
    // Add selected IDs
    ids.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    // Submit form
    document.body.appendChild(form);
    form.submit();
}