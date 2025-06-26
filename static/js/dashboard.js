// Initialize variables
let productToDelete = null;
let deleteModal = null;

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDeleteModal();
    initializeDeleteHandlers();
    initializeCharts();
});

function initializeDeleteModal() {
    const modalElement = document.getElementById('deleteModal');
    if (modalElement) {
        deleteModal = new bootstrap.Modal(modalElement);
    }
}

function initializeDeleteHandlers() {
    // Delete button click handler
    document.querySelectorAll('.delete-product').forEach(function(button) {
        button.addEventListener('click', function() {
            productToDelete = this.getAttribute('data-id');
            if (deleteModal) {
                deleteModal.show();
            }
        });
    });

    // Confirm delete handler
    const confirmDelete = document.getElementById('confirm-delete');
    if (confirmDelete) {
        confirmDelete.addEventListener('click', handleDelete);
    }
}

function handleDelete() {
    if (!productToDelete) return;
    
    // Use the correct URL from the template
    const deleteUrl = `/product/${encodeURIComponent(productToDelete)}`;
    
    fetch(deleteUrl, {
        headers: {
            'Content-Type': 'application/json',
        },
        method: 'DELETE'
    })
    .then(handleDeleteResponse)
    .catch(handleDeleteError)
    .finally(resetDeleteState);
}

function handleDeleteResponse(response) {
    if (response.ok) {
        window.location.reload();
    } else {
        return response.json().then(function(data) {
            throw new Error(data.error || 'Failed to delete product');
        });
    }
}

function handleDeleteError(error) {
    console.error('Error:', error);
    alert(error.message || 'An error occurred while deleting the product');
}

function resetDeleteState() {
    if (deleteModal) {
        deleteModal.hide();
    }
    productToDelete = null;
}

function initializeCharts() {
    const chartContainers = document.querySelectorAll('[id^="chart-"]');
    chartContainers.forEach(initializeChart);
}

function initializeChart(container) {
    const productId = container.getAttribute('data-product-id');
    if (!productId) return;
    
    const ctx = container.getContext('2d');
    
    fetch(`/product/${encodeURIComponent(productId)}/history`)
        .then(function(response) { 
            if (!response.ok) throw new Error('Failed to fetch price history');
            return response.json(); 
        })
        .then(function(history) {
            if (!history || !history.length) return;
            createPriceChart(ctx, history);
        })
        .catch(function(error) {
            console.error('Error loading chart:', error);
        });
}

function createPriceChart(ctx, history) {
    const labels = history.map(function(item) { 
        return new Date(item.date).toLocaleDateString(); 
    });
    
    const prices = history.map(function(item) { 
        return item.price; 
    });
    
    return new Chart(ctx, getChartConfig(labels, prices));
}

function getChartConfig(labels, data) {
    return {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price History',
                data: data,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                tension: 0.3,
                fill: true,
                pointBackgroundColor: '#0d6efd',
                pointBorderColor: '#fff',
                pointHoverRadius: 5,
                pointHoverBackgroundColor: '#0d6efd',
                pointHoverBorderColor: '#fff',
                pointHitRadius: 10,
                pointBorderWidth: 2,
                pointRadius: 3
            }]
        },
        options: getChartOptions()
    };
}

function getChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                mode: 'index',
                intersect: false,
                callbacks: {
                    label: function(context) {
                        return '$' + context.parsed.y.toFixed(2);
                    }
                }
            }
        },
        scales: {
            x: { display: false },
            y: {
                beginAtZero: false,
                ticks: {
                    callback: function(value) {
                        return '$' + value;
                    }
                }
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    };
}
