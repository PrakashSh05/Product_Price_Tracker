// Global variables
let currentProductId = null;

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Handle delete product button click
    document.querySelectorAll('.delete-product').forEach(button => {
        button.addEventListener('click', function() {
            currentProductId = this.dataset.id;
            const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
            deleteModal.show();
        });
    });

    // Confirm delete button
    const confirmDeleteBtn = document.getElementById('confirm-delete');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', deleteProduct);
    }

    // Initialize price update animations
    initializePriceAnimations();

    // Set up auto-refresh for dashboard
    if (window.location.pathname === '/dashboard') {
        // Refresh dashboard every 5 minutes
        setInterval(refreshDashboard, 5 * 60 * 1000);
    }
});

// Delete product function
async function deleteProduct() {
    if (!currentProductId) return;

    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
    const deleteBtn = document.getElementById('confirm-delete');
    const originalText = deleteBtn.innerHTML;
    
    try {
        // Show loading state
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Removing...';
        
        const response = await fetch(`/product/${currentProductId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (response.ok) {
            // Remove the product card from the DOM
            const productCard = document.querySelector(`[data-product-id="${currentProductId}"]`);
            if (productCard) {
                productCard.remove();
            }
            
            // Show success message
            showToast('Product removed successfully', 'success');
            
            // If no products left, show empty state
            if (document.querySelectorAll('[data-product-id]').length === 0) {
                window.location.reload();
            }
        } else {
            const data = await response.json();
            throw new Error(data.error || 'Failed to delete product');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'An error occurred while deleting the product', 'danger');
    } finally {
        // Reset button state
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalText;
        
        // Hide modal
        if (deleteModal) {
            deleteModal.hide();
        }
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 5000
    });
    
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Initialize price update animations
function initializePriceAnimations() {
    const priceElements = document.querySelectorAll('.price-value');
    
    priceElements.forEach(element => {
        // Store the current price as a data attribute
        element.dataset.lastPrice = element.textContent;
        
        // Create an observer instance
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'characterData' || mutation.type === 'childList') {
                    const newPrice = element.textContent;
                    const oldPrice = element.dataset.lastPrice;
                    
                    if (newPrice !== oldPrice) {
                        // Add animation class
                        element.classList.add('price-drop');
                        
                        // Remove animation class after animation completes
                        setTimeout(() => {
                            element.classList.remove('price-drop');
                        }, 1000);
                        
                        // Update the stored price
                        element.dataset.lastPrice = newPrice;
                    }
                }
            });
        });
        
        // Start observing the target node for configured mutations
        observer.observe(element, {
            childList: true,
            characterData: true,
            subtree: true
        });
    });
}

// Refresh dashboard data
async function refreshDashboard() {
    try {
        const response = await fetch('/dashboard-data');
        if (response.ok) {
            const data = await response.json();
            updateDashboard(data);
        }
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
    }
}

// Update dashboard with new data
function updateDashboard(data) {
    // This function would update the dashboard with fresh data
    // Implementation depends on your specific data structure and UI needs
    console.log('Updating dashboard with new data:', data);
}

// Format price
function formatPrice(price) {
    return parseFloat(price).toFixed(2);
}

// Format date
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
}
