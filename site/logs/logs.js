/**
 * Enterprise Logs Viewer - Client-side Features
 *
 * Provides filtering, search, and export functionality for the logs page.
 * Progressive enhancement - page works without JavaScript.
 */

class LogViewer {
    constructor() {
        this.logLines = Array.from(document.querySelectorAll('.log-line'));
        this.activeFilter = 'all';
        this.searchTerm = '';
        this.searchTimeout = null;

        this.initializeFilters();
        this.initializeSearch();
        this.initializeExport();
    }

    /**
     * Initialize filter button handlers
     */
    initializeFilters() {
        const filterButtons = document.querySelectorAll('.filter-btn');

        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const machine = btn.dataset.machine;
                this.setFilter(machine);

                // Update active states
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
    }

    /**
     * Set active filter and show/hide log lines
     */
    setFilter(machine) {
        this.activeFilter = machine;
        this.applyFilters();
    }

    /**
     * Initialize search box handler
     */
    initializeSearch() {
        const searchBox = document.getElementById('searchBox');

        searchBox.addEventListener('input', (e) => {
            // Debounce search for performance
            clearTimeout(this.searchTimeout);

            this.searchTimeout = setTimeout(() => {
                this.searchTerm = e.target.value.toLowerCase();
                this.applyFilters();
            }, 300);
        });
    }

    /**
     * Apply both machine filter and search term
     */
    applyFilters() {
        let visibleCount = 0;

        this.logLines.forEach(line => {
            const machine = line.dataset.machine;
            const message = line.querySelector('.message').textContent.toLowerCase();
            const timestamp = line.querySelector('.timestamp').textContent.toLowerCase();

            // Check machine filter
            const machineMatches = this.activeFilter === 'all' || machine === this.activeFilter;

            // Check search term (search in message and timestamp)
            const searchMatches = !this.searchTerm ||
                message.includes(this.searchTerm) ||
                timestamp.includes(this.searchTerm) ||
                machine.toLowerCase().includes(this.searchTerm);

            // Show/hide based on both filters
            if (machineMatches && searchMatches) {
                line.classList.remove('hidden');
                visibleCount++;
            } else {
                line.classList.add('hidden');
            }
        });

        // Log filter results (helpful for debugging)
        console.log(`Showing ${visibleCount} of ${this.logLines.length} log lines`);
    }

    /**
     * Initialize export button handler
     */
    initializeExport() {
        const exportBtn = document.getElementById('exportBtn');

        exportBtn.addEventListener('click', () => {
            this.exportLogs();
        });
    }

    /**
     * Export visible logs to .txt file
     */
    exportLogs() {
        // Get all visible log lines
        const visibleLines = this.logLines.filter(line => !line.classList.contains('hidden'));

        if (visibleLines.length === 0) {
            alert('No logs to export. Try adjusting your filters.');
            return;
        }

        // Build text content
        const lines = visibleLines.map(line => {
            const fullTimestamp = line.dataset.fullTimestamp;
            const timestamp = line.querySelector('.timestamp').textContent;
            const machine = line.querySelector('.machine-badge').textContent;
            const message = line.querySelector('.message').textContent;

            // Remove evidence icon from message if present
            const cleanMessage = message.replace(/\s*⭐\s*$/, '');

            // Format: [YYYY-MM-DD HH:MM:SS MACHINE] message
            // Prefer the full timestamp captured from merged logs.
            if (fullTimestamp) {
                return `[${fullTimestamp} ${machine}] ${cleanMessage}`;
            }

            // Fallback if data attribute is unavailable.
            return `[${timestamp} ${machine}] ${cleanMessage}`;
        });

        const content = lines.join('\n') + '\n';

        // Create blob and download
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);

        // Create temporary download link
        const a = document.createElement('a');
        a.href = url;

        // Generate filename based on filter
        const filterSuffix = this.activeFilter === 'all' ? 'all' : this.activeFilter.toLowerCase();
        const searchSuffix = this.searchTerm ? `-search` : '';
        a.download = `build-logs-${filterSuffix}${searchSuffix}.txt`;

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // Clean up blob URL
        URL.revokeObjectURL(url);

        console.log(`Exported ${visibleLines.length} log lines to ${a.download}`);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const viewer = new LogViewer();
    console.log('Log viewer initialized');
});
