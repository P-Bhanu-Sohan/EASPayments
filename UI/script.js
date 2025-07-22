document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://localhost:8000';

    async function fetchDataAndRenderTable(endpoint, tableId) {
        try {
            const response = await fetch(`${API_BASE_URL}/${endpoint}`);
            const data = await response.json();
            renderTable(data, tableId);
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            document.getElementById(tableId).innerHTML = `<p>Error loading ${endpoint} data.</p>`;
        }
    }

    function renderTable(data, tableId) {
        const tableContainer = document.getElementById(tableId);
        if (!data || data.length === 0) {
            tableContainer.innerHTML = '<p>No data available.</p>';
            return;
        }

        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');

        // Create table headers
        const headers = Object.keys(data[0]);
        const headerRow = document.createElement('tr');
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Create table rows
        data.forEach(rowData => {
            const row = document.createElement('tr');
            headers.forEach(headerText => {
                const td = document.createElement('td');
                let cellContent = rowData[headerText];

                // Handle null values
                if (cellContent === null) {
                    cellContent = '';
                }

                // Handle JSON objects in 'response' column
                if (headerText === 'response' && typeof cellContent === 'object') {
                    cellContent = JSON.stringify(cellContent, null, 2); // Pretty print JSON
                }

                td.textContent = cellContent;
                row.appendChild(td);
            });
            tbody.appendChild(row);
        });
        table.appendChild(tbody);

        tableContainer.innerHTML = ''; // Clear previous content
        tableContainer.appendChild(table);
    }

    function makeTableCollapsible(tableId) {
        const tableContainer = document.getElementById(tableId);
        const h2 = tableContainer.previousElementSibling;
        h2.classList.add('collapsible');
        h2.addEventListener('click', () => {
            tableContainer.classList.toggle('collapsed');
        });
    }

    // Fetch and render data for each table
    fetchDataAndRenderTable('accounts', 'accounts-table');
    fetchDataAndRenderTable('ledger_entries', 'ledger-entries-table');
    fetchDataAndRenderTable('idempotency_keys', 'idempotency-keys-table');
    fetchDataAndRenderTable('notifications', 'notifications-table');

    // Make tables collapsible
    makeTableCollapsible('accounts-table');
    makeTableCollapsible('ledger-entries-table');
    makeTableCollapsible('idempotency-keys-table');
    makeTableCollapsible('notifications-table');
});