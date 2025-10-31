/**
 * Show inventory adjustment modal
 * @param {Array} ids - IDs of selected items
 */
function showAdjustStockModal(ids) {
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
                                <option value="add">Increase Stock</option>
                                <option value="subtract">Decrease Stock</option>
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
 * Submit inventory adjustment request
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
        
            // Add password rule hint
        if (!field.getAttribute('aria-describedby')) {
            const passwordHelpId = `password-help-${Math.random().toString(36).substr(2, 9)}`;
            field.setAttribute('aria-describedby', passwordHelpId);
            
            const passwordHelp = document.createElement('div');
            passwordHelp.id = passwordHelpId;
            passwordHelp.className = 'form-text';
            passwordHelp.innerHTML = 'Password must be at least 8 characters long, including uppercase and lowercase letters, numbers, and special characters';
            
            field.parentNode.parentNode.appendChild(passwordHelp);
        }
    });
}

/**
 * Check password strength
 * @param {string} password - Password
 * @returns {number} - Password strength score (0-100)
 */
function checkPasswordStrength(password) {
    let score = 0;
    
    // Base length score
    if (password.length >= 8) score += 25;
    if (password.length >= 12) score += 15;
    
    // Character diversity score
    if (/[a-z]/.test(password)) score += 10;
    if (/[A-Z]/.test(password)) score += 10;
    if (/\d/.test(password)) score += 10;
    if (/[^a-zA-Z0-9]/.test(password)) score += 15;
    
    // Complexity score
    if (/[a-z].*[A-Z]|[A-Z].*[a-z]/.test(password)) score += 5;
    if (/\d.*[a-zA-Z]|[a-zA-Z].*\d/.test(password)) score += 5;
    if (/[^a-zA-Z0-9].*[a-zA-Z0-9]|[a-zA-Z0-9].*[^a-zA-Z0-9]/.test(password)) score += 5;
    
    return Math.min(score, 100);
}

/**
 * Update password strength indicator
 * @param {HTMLElement} indicator - Strength indicator element
 * @param {HTMLElement} text - Strength text element
 * @param {number} strength - Password strength score
 */
function updatePasswordStrengthIndicator(indicator, text, strength) {
    // Update progress bar
    indicator.style.width = `${strength}%`;
    indicator.setAttribute('aria-valuenow', strength);
    
    // Update color and text
    if (strength < 30) {
        indicator.className = 'progress-bar bg-danger';
        text.textContent = 'Very Weak';
        text.className = 'text-danger';
    } else if (strength < 60) {
        indicator.className = 'progress-bar bg-warning';
        text.textContent = 'Weak';
        text.className = 'text-warning';
    } else if (strength < 80) {
        indicator.className = 'progress-bar bg-info';
        text.textContent = 'Fair';
        text.className = 'text-info';
    } else {
        indicator.className = 'progress-bar bg-success';
        text.textContent = 'Strong';
        text.className = 'text-success';
    }
}

/**
 * Add secondary confirmation for sensitive operations
 */
function addConfirmationForSensitiveActions() {
    // Sensitive operation button selectors
    const sensitiveActionSelectors = [
        'a[href*="delete"]',
        'button[formaction*="delete"]',
        'a[href*="reset"]',
        'button[formaction*="reset"]',
        '.btn-danger',
        '.sensitive-action'
    ];
    
    // Get all sensitive operation buttons
    const sensitiveButtons = document.querySelectorAll(sensitiveActionSelectors.join(', '));
    
    sensitiveButtons.forEach(button => {
        // Skip already processed buttons
        if (button.getAttribute('data-confirmation-added')) return;
        
        // Mark button as processed
        button.setAttribute('data-confirmation-added', 'true');
        
        // Get operation type
        let actionType = 'Execute this operation';
        if (button.textContent.includes('Delete') || button.textContent.includes('删除')) {
            actionType = 'Delete';
        } else if (button.textContent.includes('Reset') || button.textContent.includes('重置')) {
            actionType = 'Reset';
        }
        
        // Add click event
        button.addEventListener('click', function(e) {
            // If button is inside a form, prevent form submission
            if (this.type === 'submit') {
                e.preventDefault();
            } else if (this.tagName === 'A') {
                e.preventDefault();
            }
            
            // Show confirmation dialog
            Swal.fire({
                title: `Confirm ${actionType}`,
                text: `Are you sure you want to ${actionType.toLowerCase()}? This operation may not be reversible.`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                cancelButtonColor: '#6c757d',
                confirmButtonText: `Confirm ${actionType}`,
                cancelButtonText: 'Cancel',
                focusCancel: true
            }).then((result) => {
                if (result.isConfirmed) {
                    // If confirmed, proceed with original operation
                    if (this.type === 'submit') {
                        this.form.submit();
                    } else if (this.tagName === 'A') {
                        window.location.href = this.href;
                    }
                }
            });
        });
    });
}