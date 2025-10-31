/**
 * Show stock adjustment modal
 * @param {Array} ids - Selected item IDs
 */
function showStockAdjustmentModal(ids) {
    // Create modal HTML
    const modalHtml = `
    <div class="modal fade" id="adjustStockModal" tabindex="-1" aria-labelledby="adjustStockModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="adjustStockModalLabel">Adjust Stock</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="adjustStockForm" class="needs-validation" novalidate>
                        <div class="mb-3">
                            <label for="stockAdjustmentType" class="form-label">Adjustment Type</label>
                            <select class="form-select" id="stockAdjustmentType" required>
                                <option value="">Please select adjustment type</option>
                                <option value="add">Add Stock</option>
                                <option value="subtract">Reduce Stock</option>
                                <option value="set">Set Stock</option>
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
    
    // Get modal elements
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
 * @param {Array} ids - Selected item IDs
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

/**
 * Show alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type
 */
function showAlert(message, type = 'info') {
    Swal.fire({
        text: message,
        icon: type,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true
    });
}

/**
 * Enhance password policy and secondary confirmation mechanism
 */
function enhanceSecurityFeatures() {
    // Enhance password input fields
    enhancePasswordFields();
    
    // Add secondary confirmation for sensitive operations
    addConfirmationForSensitiveActions();
}

/**
 * Enhance password input fields
 */
function enhancePasswordFields() {
    // Get all password input fields
    const passwordFields = document.querySelectorAll('input[type="password"]');
    
    passwordFields.forEach(field => {
        // Create password strength indicator container
        const strengthContainer = document.createElement('div');
        strengthContainer.className = 'password-strength-meter mt-2 d-none';
        
        // Create password strength progress bar
        const strengthBar = document.createElement('div');
        strengthBar.className = 'progress';
        strengthBar.style.height = '5px';
        
        const strengthIndicator = document.createElement('div');
        strengthIndicator.className = 'progress-bar';
        strengthIndicator.style.width = '0%';
        strengthIndicator.setAttribute('role', 'progressbar');
        strengthIndicator.setAttribute('aria-valuenow', '0');
        strengthIndicator.setAttribute('aria-valuemin', '0');
        strengthIndicator.setAttribute('aria-valuemax', '100');
        
        strengthBar.appendChild(strengthIndicator);
        
        // Create password strength text
        const strengthText = document.createElement('small');
        strengthText.className = 'text-muted';
        
        // Add to container
        strengthContainer.appendChild(strengthBar);
        strengthContainer.appendChild(strengthText);
        
        // Add after password field
        field.parentNode.insertBefore(strengthContainer, field.nextSibling);
        
        // Add password visibility toggle button
        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'btn btn-outline-secondary password-toggle';
        toggleButton.innerHTML = '<i class="bi bi-eye"></i>';
        toggleButton.setAttribute('aria-label', 'Show password');
        
        // Wrap password field in input group
        const inputGroup = document.createElement('div');
        inputGroup.className = 'input-group';
        
        // Rearrange elements
        field.parentNode.insertBefore(inputGroup, field);
        inputGroup.appendChild(field);
        inputGroup.appendChild(toggleButton);
        
        // Add password visibility toggle functionality
        toggleButton.addEventListener('click', function() {
            const type = field.getAttribute('type') === 'password' ? 'text' : 'password';
            field.setAttribute('type', type);
            this.innerHTML = type === 'password' ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
            this.setAttribute('aria-label', type === 'password' ? 'Show password' : 'Hide password');
        });
        
        // Add password strength check
        field.addEventListener('input', function() {
            if (this.value) {
                strengthContainer.classList.remove('d-none');
                const strength = checkPasswordStrength(this.value);
                updatePasswordStrengthIndicator(strengthIndicator, strengthText, strength);
            } else {
                strengthContainer.classList.add('d-none');
            }
        });
        
        // Add password rule hints
        if (!field.getAttribute('aria-describedby')) {
            const passwordHelpId = `password-help-${Math.random().toString(36).substr(2, 9)}`;
            field.setAttribute('aria-describedby', passwordHelpId);
            
            const passwordHelp = document.createElement('div');
            passwordHelp.id = passwordHelpId;
            passwordHelp.className = 'form-text';
            passwordHelp.innerHTML = 'Password must contain at least 8 characters, including uppercase and lowercase letters, numbers, and special characters';
            
            field.parentNode.parentNode.appendChild(passwordHelp);
        }
    });
}