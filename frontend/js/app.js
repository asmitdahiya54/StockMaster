const token = localStorage.getItem("stockmaster_token");

if (!token) {
    window.location.href = "login.html";
}

const user = JSON.parse(localStorage.getItem("stockmaster_user") || "{}");

const pageContent = document.getElementById("pageContent");

const pageNames = {
    dashboard: "Dashboard",
    products: "Products",
    categories: "Categories",
    suppliers: "Suppliers",
    warehouses: "Warehouses",
    inventory: "Inventory",
    "purchase-orders": "Purchase Orders",
    sales: "Sales",
    transfers: "Warehouse Transfers",
    reports: "Reports & Analytics"
};

const endpoints = {
    products: "/products/",
    categories: "/categories/",
    suppliers: "/suppliers/",
    warehouses: "/warehouses/",
    inventory: "/inventory/",
    "purchase-orders": "/purchase-orders/",
    sales: "/sales/",
    transfers: "/transfers/"
};

document.getElementById("profileName").textContent = user.full_name || "Administrator";
document.getElementById("profileRole").textContent = user.role || "Admin";
document.getElementById("profileAvatar").textContent =
    (user.full_name || "A").charAt(0).toUpperCase();

document.getElementById("logoutBtn").addEventListener("click", () => {
    localStorage.removeItem("stockmaster_token");
    localStorage.removeItem("stockmaster_user");
    window.location.href = "login.html";
});

document.getElementById("mobileMenu").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("show");
});

document.querySelectorAll(".sidebar .nav-link").forEach(link => {
    link.addEventListener("click", event => {
        event.preventDefault();

        const page = link.dataset.page;

        document.querySelectorAll(".sidebar .nav-link").forEach(item => {
            item.classList.remove("active");
        });

        link.classList.add("active");
        document.getElementById("sidebar").classList.remove("show");

        loadPage(page);
    });
});

function money(value) {
    return Number(value || 0).toLocaleString("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
    });
}

function statusBadge(status) {
    const value = String(status || "Unknown");
    const className = ["Completed", "Received"].includes(value)
        ? "status-completed"
        : value === "Pending"
            ? "status-pending"
            : "status-other";

    return `<span class="badge-status ${className}">${value}</span>`;
}

function showError(error) {
    pageContent.innerHTML = `
        <div class="alert alert-danger">
            <strong>Unable to load data.</strong><br>
            ${error.message}
        </div>
    `;
}

async function loadPage(page) {

    document.getElementById("pageTitle").textContent = pageNames[page];
    document.getElementById("pageSubtitle").textContent =
        `StockMaster / ${pageNames[page]}`;

    pageContent.innerHTML = `
        <div class="loading-state">
            <div class="spinner-border text-primary"></div>
            <p>Loading ${pageNames[page]}...</p>
        </div>
    `;

    try {

        if (page === "dashboard") return await loadDashboard();
        if (page === "products") return await loadProductsPage();
        if (page === "categories") return await loadCategoriesPage();
        if (page === "suppliers") return await loadSuppliersPage();
        if (page === "warehouses") return await loadWarehousesPage();
        if (page === "inventory") return await loadInventoryPage();
        if (page === "purchase-orders") return await loadPurchaseOrdersPage();
        if (page === "sales") return await loadSalesPage();
        if (page === "transfers") return await loadTransfersPage();
        if (page === "reports") return await loadReportsPage();
    
        if (page === "reports") return await loadReports();

        return await loadTablePage(page);

    } catch (error) {
        showError(error);
    }
}


// DASHBOARD

async function loadDashboard() {

    const [summary, warehouseStock, lowStock] = await Promise.all([
        API.get("/dashboard/summary"),
        API.get("/dashboard/warehouse-stock"),
        API.get("/dashboard/low-stock")
    ]);

    const data = summary.data || summary;

    pageContent.innerHTML = `
        <div class="page-heading">
            <div>
                <h3>Overview</h3>
                <p>Monitor your inventory and business performance.</p>
            </div>
            <span class="badge bg-success-subtle text-success p-2">
                <i class="bi bi-check-circle"></i> Live Data
            </span>
        </div>

        <div class="row g-3 mb-4">

            <div class="col-md-6 col-xl-3">
                <div class="stat-card">
                    <div>
                        <p>Total Products</p>
                        <h3 id="totalProducts">--</h3>
                        <small class="text-muted">Registered products</small>
                    </div>
                    <div class="stat-icon"><i class="bi bi-box"></i></div>
                </div>
            </div>

            <div class="col-md-6 col-xl-3">
                <div class="stat-card">
                    <div>
                        <p>Total Stock Units</p>
                        <h3 id="totalStock">--</h3>
                        <small class="text-muted">Across warehouses</small>
                    </div>
                    <div class="stat-icon"><i class="bi bi-archive"></i></div>
                </div>
            </div>

            <div class="col-md-6 col-xl-3">
                <div class="stat-card">
                    <div>
                        <p>Warehouses</p>
                        <h3 id="totalWarehouses">--</h3>
                        <small class="text-muted">Active locations</small>
                    </div>
                    <div class="stat-icon"><i class="bi bi-building"></i></div>
                </div>
            </div>

            <div class="col-md-6 col-xl-3">
                <div class="stat-card">
                    <div>
                        <p>Low Stock Alerts</p>
                        <h3 id="lowStockCount">--</h3>
                        <small class="text-muted">Stock warnings</small>
                    </div>
                    <div class="stat-icon"><i class="bi bi-exclamation-triangle"></i></div>
                </div>
            </div>

        </div>

        <div class="row g-3">

            <div class="col-lg-8">
                <div class="content-card">
                    <h6>Warehouse Stock Distribution</h6>
                    <canvas id="warehouseChart" height="120"></canvas>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="content-card">
                    <h6>Low Stock Alerts</h6>
                    <div id="lowStockList"></div>
                </div>
            </div>

        </div>
    `;

    const summaryData = data.summary || data;

    document.getElementById("totalProducts").textContent =
        summaryData.total_products ?? "--";

    document.getElementById("totalStock").textContent =
    summaryData.total_stock_units ?? "--";

    document.getElementById("totalWarehouses").textContent =
        summaryData.total_warehouses ?? "--";

    const lowRecords = lowStock.data || [];

    document.getElementById("lowStockCount").textContent =
        lowStock.total_records ?? lowRecords.length;

    document.getElementById("lowStockList").innerHTML =
        lowRecords.slice(0, 6).map(item => `
            <div class="d-flex justify-content-between border-bottom py-3">
                <div>
                    <strong>${item.product_name}</strong>
                    <div class="text-muted small">${item.warehouse_name}</div>
                </div>
                <span class="badge bg-warning-subtle text-warning">
                ${item.quantity}
                                </span>
            </div>
        `).join("") || "<p>No low-stock alerts.</p>";

    const warehouses = warehouseStock.data || [];

    new Chart(document.getElementById("warehouseChart"), {
        type: "bar",
        data: {
            labels: warehouses.map(w =>
                w.warehouse_name || w.name
            ),
            datasets: [{
                label: "Stock Units",
                data: warehouses.map(w =>
                    Number(w.total_units ?? w.total_stock ?? 0)
                ),
                borderRadius: 7
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}


// GENERAL TABLE PAGES

async function loadTablePage(page) {

    const result = await API.get(endpoints[page]);
    const records = result.data || [];

    const columns = {
        products: ["product_id", "sku", "product_name", "unit_price", "reorder_level"],
        categories: ["category_id", "category_name", "description"],
        suppliers: ["supplier_id", "supplier_name", "email", "phone"],
        warehouses: ["warehouse_id", "warehouse_name", "location"],
        inventory: ["stock_id", "product_id", "warehouse_id", "quantity"],
        "purchase-orders": ["purchase_order_id", "supplier_name", "warehouse_name", "order_date", "status"],
        sales: ["sale_id", "customer_name", "warehouse_name", "sale_date", "status"],
        transfers: ["transfer_id", "source_warehouse", "destination_warehouse", "total_quantity", "status"]
    };

    const keys = columns[page];

    const rows = records.map(record => `
        <tr>
            ${keys.map(key => `
                <td>
                    ${key === "status"
                        ? statusBadge(record[key])
                        : key.includes("price")
                            ? money(record[key])
                            : record[key] ?? "-"}
                </td>
            `).join("")}
        </tr>
    `).join("");

    pageContent.innerHTML = `
        <div class="page-heading">
            <div>
                <h3>${pageNames[page]}</h3>
                <p>View and manage ${pageNames[page].toLowerCase()}.</p>
            </div>
            <button class="btn btn-primary" onclick="refreshCurrentPage()">
                <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
        </div>

        <div class="content-card">
            <div class="d-flex justify-content-between mb-3 flex-wrap gap-2">
                <h6>${pageNames[page]} List</h6>
                <input
                    type="search"
                    id="tableSearch"
                    class="form-control search-input"
                    placeholder="Search visible records..."
                >
            </div>

            <div class="table-responsive">
                <table class="table table-hover" id="dataTable">
                    <thead>
                        <tr>
                            ${keys.map(key => `
                                <th>${key.replaceAll("_", " ")}</th>
                            `).join("")}
                        </tr>
                    </thead>
                    <tbody>
                        ${rows || `
                            <tr>
                                <td colspan="${keys.length}" class="text-center">
                                    No records found.
                                </td>
                            </tr>
                        `}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    document.getElementById("tableSearch").addEventListener("input", event => {
        const search = event.target.value.toLowerCase();

        document.querySelectorAll("#dataTable tbody tr").forEach(row => {
            row.style.display =
                row.textContent.toLowerCase().includes(search) ? "" : "none";
        });
    });
}


// REPORTS

async function loadReports() {

    const [valuation, sales, suppliers, warehouses, products] =
        await Promise.all([
            API.get("/reports/inventory-valuation"),
            API.get("/reports/sales-summary"),
            API.get("/reports/supplier-performance"),
            API.get("/reports/warehouse-performance"),
            API.get("/reports/product-performance")
        ]);

    const inventory = valuation.data.summary;
    const salesData = sales.data.summary;

    pageContent.innerHTML = `
        <div class="page-heading">
            <div>
                <h3>Reports & Analytics</h3>
                <p>Business performance and inventory insights.</p>
            </div>
        </div>

        <div class="row g-3 mb-4">

            <div class="col-md-6 col-xl-3">
                <div class="content-card">
                    <p class="text-muted">Inventory Valuation</p>
                    <div class="report-value">${money(inventory.total_value)}</div>
                </div>
            </div>

            <div class="col-md-6 col-xl-3">
                <div class="content-card">
                    <p class="text-muted">Total Stock Units</p>
                    <div class="report-value">${Number(inventory.total_units).toLocaleString("en-IN")}</div>
                </div>
            </div>

            <div class="col-md-6 col-xl-3">
                <div class="content-card">
                    <p class="text-muted">Sales Revenue</p>
                    <div class="report-value">${money(salesData.completed_revenue)}</div>
                </div>
            </div>

            <div class="col-md-6 col-xl-3">
                <div class="content-card">
                    <p class="text-muted">Completed Orders</p>
                    <div class="report-value">${salesData.completed_orders}</div>
                </div>
            </div>

        </div>

        <div class="row g-3">

            <div class="col-lg-6">
                <div class="content-card">
                    <h6>Warehouse Inventory Valuation</h6>
                    <canvas id="valuationChart"></canvas>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="content-card">
                    <h6>Warehouse Revenue</h6>
                    <canvas id="revenueChart"></canvas>
                </div>
            </div>

            <div class="col-12">
                <div class="content-card">
                    <h6>Fast Moving Products</h6>
                    <div id="fastProducts"></div>
                </div>
            </div>

            <div class="col-12">
                <div class="content-card">
                    <h6>Supplier Performance</h6>
                    <div id="supplierTable"></div>
                </div>
            </div>

        </div>
    `;

    const warehouseData = warehouses.data || [];

    new Chart(document.getElementById("valuationChart"), {
        type: "doughnut",
        data: {
            labels: warehouseData.map(w => w.warehouse_name),
            datasets: [{
                data: warehouseData.map(w => Number(w.inventory_value))
            }]
        },
        options: { responsive: true }
    });

    new Chart(document.getElementById("revenueChart"), {
        type: "bar",
        data: {
            labels: warehouseData.map(w => w.warehouse_name),
            datasets: [{
                label: "Revenue",
                data: warehouseData.map(w => Number(w.completed_revenue))
            }]
        },
        options: { responsive: true }
    });

    document.getElementById("fastProducts").innerHTML =
        products.data.fast_moving_products.slice(0, 5).map(p => `
            <div class="d-flex justify-content-between border-bottom py-2">
                <span>${p.product_name}</span>
                <strong>${p.units_sold} units sold</strong>
            </div>
        `).join("");

    document.getElementById("supplierTable").innerHTML = `
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th>Supplier</th>
                        <th>Total Orders</th>
                        <th>Received Orders</th>
                        <th>Purchase Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${suppliers.data.map(s => `
                        <tr>
                            <td>${s.supplier_name}</td>
                            <td>${s.total_orders}</td>
                            <td>${s.received_orders}</td>
                            <td>${money(s.received_purchase_value)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

let currentPage = "dashboard";

async function refreshCurrentPage() {
    await loadPage(currentPage);
}

const originalLoadPage = loadPage;

loadPage = async function(page) {
    currentPage = page;
    return originalLoadPage(page);
};

loadPage("dashboard");
