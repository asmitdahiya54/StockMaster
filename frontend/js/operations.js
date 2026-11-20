
function safeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
    })[c]);
}

function responseRows(result) {
    return result.data || [];
}

async function getAllPages(endpoint) {
    const first = await API.get(endpoint);
    let records = [...responseRows(first)];
    const pages = first.pagination?.total_pages || 1;

    for (let page = 2; page <= pages; page++) {
        const next = await API.get(
            `${endpoint}${endpoint.includes("?") ? "&" : "?"}page=${page}`
        );
        records.push(...responseRows(next));
    }
    return records;
}

function showNotice(message, type = "success") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `alert alert-${type} shadow`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function tableHTML(columns, records, actions = false) {
    if (!records.length) {
        return `<tr><td colspan="${columns.length + (actions ? 1 : 0)}"
            class="text-center py-4">No records found.</td></tr>`;
    }

    return records.map(row => `
        <tr>
            ${columns.map(column => {
                let value = row[column.key];

                if (column.money) value = money(value);
                else if (column.status) value = statusBadge(value);
                else value = safeHTML(value ?? "-");

                return `<td>${value}</td>`;
            }).join("")}
            ${actions ? `<td>${actions(row)}</td>` : ""}
        </tr>
    `).join("");
}

function renderOperationsPage(title, subtitle, columns, records, options = {}) {
    const canManage = options.canManage ?? false;
    const canDelete = options.canDelete ?? false;

    pageContent.innerHTML = `
        <div class="page-heading">
            <div>
                <h3>${title}</h3>
                <p>${subtitle}</p>
            </div>
            <div class="d-flex gap-2">
                <button class="btn btn-outline-primary" id="operationRefresh">
                    <i class="bi bi-arrow-clockwise"></i> Refresh
                </button>
                ${options.addLabel && canManage ? `
                    <button class="btn btn-primary" id="operationAdd">
                        <i class="bi bi-plus-lg"></i> ${options.addLabel}
                    </button>
                ` : ""}
            </div>
        </div>

        ${options.stats || ""}

        <div class="content-card">
            <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                <h6 class="mb-0">${title} List</h6>
                <input id="operationSearch" class="form-control search-input"
                    type="search" placeholder="Search records...">
            </div>

            <div class="table-responsive">
                <table class="table table-hover">
                    <thead><tr>
                        ${columns.map(c => `<th>${c.label}</th>`).join("")}
                        ${options.actions ? "<th>Actions</th>" : ""}
                    </tr></thead>
                    <tbody id="operationTableBody">
                        ${tableHTML(columns, records, options.actions)}
                    </tbody>
                </table>
            </div>
            <div class="text-muted small" id="operationCount"></div>
        </div>
    `;

    const search = document.getElementById("operationSearch");
    const body = document.getElementById("operationTableBody");

    function filter() {
        const term = search.value.toLowerCase();
        const filtered = records.filter(row =>
            Object.values(row).some(value =>
                String(value ?? "").toLowerCase().includes(term)
            )
        );
        body.innerHTML = tableHTML(columns, filtered, options.actions);
        document.getElementById("operationCount").textContent =
            `Showing ${filtered.length} records`;
    }

    search.addEventListener("input", filter);

    document.getElementById("operationRefresh").onclick =
        () => loadPage(currentPage);

    if (options.addLabel && canManage) {
        document.getElementById("operationAdd").onclick = options.onAdd;
    }

    if (options.onAction) {
        body.addEventListener("click", event => {
            const button = event.target.closest("[data-action]");
            if (!button) return;
            options.onAction(button.dataset.action, Number(button.dataset.id));
        });
    }

    filter();
}

function operationModal(title, fields, initial = {}) {
    const old = document.getElementById("operationModal");
    if (old) old.remove();

    const modal = document.createElement("div");
    modal.id = "operationModal";
    modal.className = "product-modal";

    modal.innerHTML = `
        <div class="product-modal-card">
            <div class="d-flex justify-content-between mb-4">
                <h5>${title}</h5>
                <button class="btn-close" id="operationClose"></button>
            </div>

            <form id="operationForm">
                ${fields.map(field => `
                    <div class="mb-3">
                        <label class="form-label">${field.label}</label>
                        ${field.type === "select" ? `
                            <select class="form-select" id="${field.id}"
                                ${field.required ? "required" : ""}>
                                <option value="">Select ${field.label}</option>
                                ${field.options.map(option => `
                                    <option value="${safeHTML(option.value)}"
                                        ${String(initial[field.id] ?? "") === String(option.value) ? "selected" : ""}>
                                        ${safeHTML(option.label)}
                                    </option>
                                `).join("")}
                            </select>
                        ` : field.type === "textarea" ? `
                            <textarea class="form-control" id="${field.id}"
                                rows="3">${safeHTML(initial[field.id] || "")}</textarea>
                        ` : `
                            <input class="form-control" id="${field.id}"
                                type="${field.type || "text"}"
                                value="${safeHTML(initial[field.id] ?? "")}"
                                ${field.required ? "required" : ""}
                                ${field.min !== undefined ? `min="${field.min}"` : ""}
                                ${field.step ? `step="${field.step}"` : ""}>
                        `}
                    </div>
                `).join("")}

                <div id="operationError" class="alert alert-danger d-none"></div>

                <div class="d-flex justify-content-end gap-2">
                    <button type="button" class="btn btn-light" id="operationCancel">
                        Cancel
                    </button>
                    <button type="submit" class="btn btn-primary" id="operationSave">
                        Save
                    </button>
                </div>
            </form>
        </div>
    `;

    document.body.appendChild(modal);

    const close = () => modal.remove();
    document.getElementById("operationClose").onclick = close;
    document.getElementById("operationCancel").onclick = close;

    return {
        modal,
        close,
        form: document.getElementById("operationForm"),
        error: document.getElementById("operationError"),
        save: document.getElementById("operationSave")
    };
}

function formValue(id) {
    return document.getElementById(id).value.trim();
}

function selectOptions(records, idKey, nameKey) {
    return records.map(row => ({
        value: row[idKey],
        label: row[nameKey]
    }));
}

async function submitModal(modal, action) {
    modal.form.addEventListener("submit", async event => {
        event.preventDefault();
        modal.save.disabled = true;
        modal.save.textContent = "Saving...";
        modal.error.classList.add("d-none");

        try {
            await action();
            modal.close();
            showNotice("Operation completed successfully.");
            await loadPage(currentPage);
        } catch (error) {
            modal.error.textContent = error.message;
            modal.error.classList.remove("d-none");
        } finally {
            modal.save.disabled = false;
            modal.save.textContent = "Save";
        }
    });
}


// SUPPLIERS

async function loadSuppliersPage() {
    const records = await getAllPages("/suppliers/");
    const isAdmin = user.role === "Admin";
    const canManage = ["Admin", "Manager"].includes(user.role);

    const columns = [
        {key:"supplier_id", label:"ID"},
        {key:"supplier_name", label:"Supplier"},
        {key:"contact_person", label:"Contact Person"},
        {key:"email", label:"Email"},
        {key:"phone", label:"Phone"},
        {key:"address", label:"Address"}
    ];

    renderOperationsPage(
        "Suppliers",
        "Manage your supplier directory and contact information.",
        columns, records, {
            canManage, canDelete:isAdmin, addLabel:"Add Supplier",
            actions: row => `
                ${canManage ? `<button class="action-button"
                    data-action="edit" data-id="${row.supplier_id}">
                    <i class="bi bi-pencil"></i></button>` : ""}
                ${isAdmin ? `<button class="action-button text-danger"
                    data-action="delete" data-id="${row.supplier_id}">
                    <i class="bi bi-trash"></i></button>` : ""}
            `,
            onAdd: () => supplierForm(),
            onAction: async (action, id) => {
                const row = records.find(x => Number(x.supplier_id) === id);
                if (!row) return;
                if (action === "edit") supplierForm(row);
                if (action === "delete") {
                    if (!confirm(`Delete supplier ${row.supplier_name}?`)) return;
                    try {
                        await API.delete(`/suppliers/${id}`);
                        showNotice("Supplier deleted.");
                        loadPage("suppliers");
                    } catch (e) { showNotice(e.message, "danger"); }
                }
            }
        }
    );
}

function supplierForm(row = {}) {
    const editing = Boolean(row.supplier_id);
    const modal = operationModal(editing ? "Edit Supplier" : "Add Supplier", [
        {id:"supplier_name",label:"Supplier Name",required:true},
        {id:"contact_person",label:"Contact Person"},
        {id:"email",label:"Email",type:"email"},
        {id:"phone",label:"Phone"},
        {id:"address",label:"Address",type:"textarea"}
    ], row);

    submitModal(modal, async () => {
        const payload = {
            supplier_name:formValue("supplier_name"),
            contact_person:formValue("contact_person"),
            email:formValue("email"),
            phone:formValue("phone"),
            address:formValue("address")
        };
        if (!payload.supplier_name) throw Error("Supplier name is required.");
        if (editing) await API.put(`/suppliers/${row.supplier_id}`, payload);
        else await API.post("/suppliers/", payload);
    });
}


// WAREHOUSES

async function loadWarehousesPage() {
    const records = await getAllPages("/warehouses/");
    const isAdmin = user.role === "Admin";
    const canManage = ["Admin", "Manager"].includes(user.role);

    const columns = [
        {key:"warehouse_id",label:"ID"},
        {key:"warehouse_name",label:"Warehouse"},
        {key:"location",label:"Location"},
        {key:"contact_number",label:"Contact Number"},
        {key:"total_units",label:"Stock Units"}
    ];

    renderOperationsPage(
        "Warehouses",
        "Manage warehouse locations and storage facilities.",
        columns, records, {
            canManage, canDelete:isAdmin, addLabel:"Add Warehouse",
            actions: row => `
                ${canManage ? `<button class="action-button"
                    data-action="edit" data-id="${row.warehouse_id}">
                    <i class="bi bi-pencil"></i></button>` : ""}
                ${isAdmin ? `<button class="action-button text-danger"
                    data-action="delete" data-id="${row.warehouse_id}">
                    <i class="bi bi-trash"></i></button>` : ""}
            `,
            onAdd: () => warehouseForm(),
            onAction: async (action, id) => {
                const row = records.find(x => Number(x.warehouse_id) === id);
                if (!row) return;
                if (action === "edit") warehouseForm(row);
                if (action === "delete") {
                    if (!confirm(`Delete warehouse ${row.warehouse_name}?`)) return;
                    try {
                        await API.delete(`/warehouses/${id}`);
                        showNotice("Warehouse deleted.");
                        loadPage("warehouses");
                    } catch (e) { showNotice(e.message, "danger"); }
                }
            }
        }
    );
}

function warehouseForm(row = {}) {
    const editing = Boolean(row.warehouse_id);
    const modal = operationModal(editing ? "Edit Warehouse" : "Add Warehouse", [
        {id:"warehouse_name",label:"Warehouse Name",required:true},
        {id:"location",label:"Location",required:true},
        {id:"contact_number",label:"Contact Number"}
    ], row);

    submitModal(modal, async () => {
        const payload = {
            warehouse_name:formValue("warehouse_name"),
            location:formValue("location"),
            contact_number:formValue("contact_number")
        };
        if (!payload.warehouse_name || !payload.location)
            throw Error("Warehouse name and location are required.");
        if (editing) await API.put(`/warehouses/${row.warehouse_id}`, payload);
        else await API.post("/warehouses/", payload);
    });
}


// INVENTORY

async function loadInventoryPage() {
    const [records, products, warehouses, movements] = await Promise.all([
        getAllPages("/inventory/"),
        getAllPages("/products/"),
        getAllPages("/warehouses/"),
        API.get("/inventory/movements")
    ]);

    const movementRows = responseRows(movements);
    const canTransact = ["Admin","Manager","Staff"].includes(user.role);
    const canAdjust = ["Admin","Manager"].includes(user.role);

    const stats = `
        <div class="row g-3 mb-4">
            <div class="col-md-4"><div class="stat-card">
                <div><p>Stock Records</p><h3>${records.length}</h3></div>
                <div class="stat-icon"><i class="bi bi-archive"></i></div>
            </div></div>
            <div class="col-md-4"><div class="stat-card">
                <div><p>Total Stock Units</p><h3>${records.reduce((s,r)=>s+Number(r.quantity||0),0).toLocaleString("en-IN")}</h3></div>
                <div class="stat-icon"><i class="bi bi-boxes"></i></div>
            </div></div>
            <div class="col-md-4"><div class="stat-card">
                <div><p>Movement Records</p><h3>${movementRows.length}</h3></div>
                <div class="stat-icon"><i class="bi bi-arrow-left-right"></i></div>
            </div></div>
        </div>
    `;

    const columns = [
        {key:"product_name",label:"Product"},
        {key:"sku",label:"SKU"},
        {key:"warehouse_name",label:"Warehouse"},
        {key:"quantity",label:"Available Quantity"},
        {key:"reorder_level",label:"Reorder Level"}
    ];

    renderOperationsPage("Inventory","Monitor and manage stock across warehouses.",
        columns,records,{
            canManage:canTransact,
            stats,
            addLabel:"Stock Transaction",
            onAdd:()=>inventoryForm(products,warehouses,canAdjust)
        });

    const card = pageContent.querySelector(".content-card");
    card.insertAdjacentHTML("beforeend",`
        <hr>
        <h6>Recent Stock Movements</h6>
        <div class="table-responsive">
            <table class="table">
                <thead><tr><th>Date</th><th>Product</th><th>Warehouse</th>
                <th>Type</th><th>Quantity</th><th>Reference</th></tr></thead>
                <tbody>
                    ${tableHTML([
                        {key:"movement_date",label:"Date"},
                        {key:"product_name",label:"Product"},
                        {key:"warehouse_name",label:"Warehouse"},
                        {key:"movement_type",label:"Type"},
                        {key:"quantity",label:"Quantity"},
                        {key:"reference_note",label:"Reference"}
                    ],movementRows)}
                </tbody>
            </table>
        </div>
    `);
}

function inventoryForm(products,warehouses,canAdjust) {
    const modal = operationModal("Stock Transaction",[
        {id:"movement_type",label:"Transaction Type",type:"select",required:true,
            options:[
                {value:"stock-in",label:"Stock In"},
                {value:"stock-out",label:"Stock Out"},
                ...(canAdjust?[{value:"adjustment",label:"Stock Adjustment"}]:[])
            ]},
        {id:"product_id",label:"Product",type:"select",required:true,
            options:selectOptions(products,"product_id","product_name")},
        {id:"warehouse_id",label:"Warehouse",type:"select",required:true,
            options:selectOptions(warehouses,"warehouse_id","warehouse_name")},
        {id:"quantity",label:"Quantity",type:"number",required:true,min:"1",step:"1"},
        {id:"reference_note",label:"Reference / Note"}
    ]);

    submitModal(modal,async()=>{
        const type=formValue("movement_type");
        const quantity=Number(formValue("quantity"));
        if(!Number.isInteger(quantity)||quantity<=0) throw Error("Enter a positive whole-number quantity.");

        await API.post(`/inventory/${type}`,{
            product_id:Number(formValue("product_id")),
            warehouse_id:Number(formValue("warehouse_id")),
            quantity,
            reference_note:formValue("reference_note")
        });
    });
}


// PURCHASE ORDERS

async function loadPurchaseOrdersPage() {
    const records=await getAllPages("/purchase-orders/");
    const canManage=["Admin","Manager"].includes(user.role);

    renderOperationsPage("Purchase Orders","Create orders and receive incoming stock.",[
        {key:"purchase_order_id",label:"Order ID"},
        {key:"supplier_name",label:"Supplier"},
        {key:"warehouse_name",label:"Warehouse"},
        {key:"order_date",label:"Order Date"},
        {key:"total_quantity",label:"Quantity"},
        {key:"total_cost",label:"Order Value",money:true},
        {key:"status",label:"Status",status:true}
    ],records,{
        canManage,addLabel:"Create Order",
        actions:row=>row.status==="Pending"&&canManage?`
            <button class="btn btn-sm btn-success"
                data-action="receive" data-id="${row.purchase_order_id}">
                Receive
            </button>`:`<span class="text-muted">?</span>`,
        onAdd:()=>purchaseOrderForm(),
        onAction:async(action,id)=>{
            if(action!=="receive")return;
            if(!confirm(`Receive purchase order #${id}? This will increase stock.`))return;
            try{
                await API.post(`/purchase-orders/${id}/receive`,{});
                showNotice("Purchase order received and stock updated.");
                loadPage("purchase-orders");
            }catch(e){showNotice(e.message,"danger");}
        }
    });
}

async function purchaseOrderForm() {
    const [suppliers,warehouses,products]=await Promise.all([
        getAllPages("/suppliers/"),getAllPages("/warehouses/"),getAllPages("/products/")
    ]);

    const modal=operationModal("Create Purchase Order",[
        {id:"supplier_id",label:"Supplier",type:"select",required:true,
            options:selectOptions(suppliers,"supplier_id","supplier_name")},
        {id:"warehouse_id",label:"Destination Warehouse",type:"select",required:true,
            options:selectOptions(warehouses,"warehouse_id","warehouse_name")},
        {id:"expected_date",label:"Expected Date",type:"date"},
        {id:"product_id",label:"Product",type:"select",required:true,
            options:selectOptions(products,"product_id","product_name")},
        {id:"quantity",label:"Quantity",type:"number",required:true,min:"1",step:"1"},
        {id:"unit_cost",label:"Unit Cost (?)",type:"number",required:true,min:"0.01",step:"0.01"}
    ]);

    submitModal(modal,async()=>{
        const quantity=Number(formValue("quantity"));
        const unit_cost=Number(formValue("unit_cost"));
        if(!Number.isInteger(quantity)||quantity<=0||unit_cost<=0)
            throw Error("Enter valid quantity and unit cost.");

        await API.post("/purchase-orders/",{
            supplier_id:Number(formValue("supplier_id")),
            warehouse_id:Number(formValue("warehouse_id")),
            expected_date:formValue("expected_date")||null,
            items:[{
                product_id:Number(formValue("product_id")),
                quantity,unit_cost
            }]
        });
    });
}


// SALES

async function loadSalesPage() {
    const records=await getAllPages("/sales/");
    const canSell=["Admin","Manager","Staff"].includes(user.role);

    renderOperationsPage("Sales","Manage customer sales and order history.",[
        {key:"sale_id",label:"Sale ID"},
        {key:"customer_name",label:"Customer"},
        {key:"warehouse_name",label:"Warehouse"},
        {key:"sale_date",label:"Sale Date"},
        {key:"total_quantity",label:"Units"},
        {key:"total_amount",label:"Total Amount",money:true},
        {key:"status",label:"Status",status:true}
    ],records,{
        canManage:canSell,addLabel:"Create Sale",
        onAdd:()=>saleForm()
    });
}

async function saleForm() {
    const [customers,warehouses,products]=await Promise.all([
        getAllPages("/customers/"),getAllPages("/warehouses/"),getAllPages("/products/")
    ]);

    const modal=operationModal("Create Sale",[
        {id:"customer_id",label:"Customer",type:"select",required:true,
            options:selectOptions(customers,"customer_id","customer_name")},
        {id:"warehouse_id",label:"Warehouse",type:"select",required:true,
            options:selectOptions(warehouses,"warehouse_id","warehouse_name")},
        {id:"product_id",label:"Product",type:"select",required:true,
            options:selectOptions(products,"product_id","product_name")},
        {id:"quantity",label:"Quantity",type:"number",required:true,min:"1",step:"1"},
        {id:"unit_price",label:"Selling Price (?)",type:"number",required:true,min:"0.01",step:"0.01"}
    ]);

    submitModal(modal,async()=>{
        const quantity=Number(formValue("quantity"));
        const unit_price=Number(formValue("unit_price"));
        if(!Number.isInteger(quantity)||quantity<=0||unit_price<=0)
            throw Error("Enter a valid quantity and selling price.");

        await API.post("/sales/",{
            customer_id:Number(formValue("customer_id")),
            warehouse_id:Number(formValue("warehouse_id")),
            items:[{
                product_id:Number(formValue("product_id")),
                quantity,unit_price
            }]
        });
    });
}


// TRANSFERS

async function loadTransfersPage() {
    const records=await getAllPages("/transfers/");
    const canManage=["Admin","Manager"].includes(user.role);

    renderOperationsPage("Warehouse Transfers",
        "Move inventory between warehouse locations.",[
        {key:"transfer_id",label:"Transfer ID"},
        {key:"source_warehouse",label:"Source"},
        {key:"destination_warehouse",label:"Destination"},
        {key:"total_quantity",label:"Quantity"},
        {key:"transfer_date",label:"Date"},
        {key:"status",label:"Status",status:true}
    ],records,{
        canManage,addLabel:"New Transfer",
        actions:row=>row.status==="Pending"&&canManage?`
            <button class="btn btn-sm btn-success"
                data-action="complete" data-id="${row.transfer_id}">
                Complete
            </button>`:"?",
        onAdd:()=>transferForm(),
        onAction:async(action,id)=>{
            if(action!=="complete")return;
            if(!confirm(`Complete transfer #${id}? Stock will move between warehouses.`))return;
            try{
                await API.post(`/transfers/${id}/complete`,{});
                showNotice("Transfer completed successfully.");
                loadPage("transfers");
            }catch(e){showNotice(e.message,"danger");}
        }
    });
}

async function transferForm() {
    const [warehouses,products]=await Promise.all([
        getAllPages("/warehouses/"),getAllPages("/products/")
    ]);

    const modal=operationModal("Create Warehouse Transfer",[
        {id:"source_warehouse_id",label:"Source Warehouse",type:"select",required:true,
            options:selectOptions(warehouses,"warehouse_id","warehouse_name")},
        {id:"destination_warehouse_id",label:"Destination Warehouse",type:"select",required:true,
            options:selectOptions(warehouses,"warehouse_id","warehouse_name")},
        {id:"product_id",label:"Product",type:"select",required:true,
            options:selectOptions(products,"product_id","product_name")},
        {id:"quantity",label:"Quantity",type:"number",required:true,min:"1",step:"1"}
    ]);

    submitModal(modal,async()=>{
        const source=Number(formValue("source_warehouse_id"));
        const destination=Number(formValue("destination_warehouse_id"));
        const quantity=Number(formValue("quantity"));

        if(source===destination)throw Error("Choose two different warehouses.");
        if(!Number.isInteger(quantity)||quantity<=0)throw Error("Enter a positive whole-number quantity.");

        await API.post("/transfers/",{
            source_warehouse_id:source,
            destination_warehouse_id:destination,
            items:[{
                product_id:Number(formValue("product_id")),
                quantity
            }]
        });
    });
}


// REPORTS

async function loadReportsPage() {
    const [valuation,sales,monthly,products,suppliers,warehouses]=await Promise.all([
        API.get("/reports/inventory-valuation"),
        API.get("/reports/sales-summary"),
        API.get("/reports/monthly-sales"),
        API.get("/reports/product-performance"),
        API.get("/reports/supplier-performance"),
        API.get("/reports/warehouse-performance")
    ]);

    const inv=valuation.data.summary;
    const sale=sales.data.summary;
    const warehouseRows=warehouses.data||[];
    const monthlyRows=monthly.data||[];
    const fast=products.data.fast_moving_products||[];
    const supplierRows=suppliers.data||[];

    pageContent.innerHTML=`
        <div class="page-heading">
            <div><h3>Reports & Analytics</h3>
            <p>Inventory, sales and operational performance.</p></div>
            <button class="btn btn-outline-primary" onclick="loadPage('reports')">
                <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-md-6 col-xl-3"><div class="content-card">
                <p class="text-muted">Inventory Value</p>
                <div class="report-value">${money(inv.total_value)}</div>
            </div></div>
            <div class="col-md-6 col-xl-3"><div class="content-card">
                <p class="text-muted">Stock Units</p>
                <div class="report-value">${Number(inv.total_units).toLocaleString("en-IN")}</div>
            </div></div>
            <div class="col-md-6 col-xl-3"><div class="content-card">
                <p class="text-muted">Completed Sales Revenue</p>
                <div class="report-value">${money(sale.completed_revenue)}</div>
            </div></div>
            <div class="col-md-6 col-xl-3"><div class="content-card">
                <p class="text-muted">Completed Orders</p>
                <div class="report-value">${sale.completed_orders}</div>
            </div></div>
        </div>

        <div class="row g-3">
            <div class="col-lg-6"><div class="content-card">
                <h6>Warehouse Inventory Valuation</h6>
                <canvas id="reportValuationChart"></canvas>
            </div></div>
            <div class="col-lg-6"><div class="content-card">
                <h6>Warehouse Sales Revenue</h6>
                <canvas id="reportRevenueChart"></canvas>
            </div></div>
            <div class="col-12"><div class="content-card">
                <h6>Monthly Sales</h6>
                <canvas id="monthlySalesChart"></canvas>
            </div></div>
            <div class="col-12"><div class="content-card">
                <h6>Fast Moving Products</h6>
                <div class="table-responsive"><table class="table">
                <thead><tr><th>Product</th><th>Units Sold</th></tr></thead>
                <tbody>${tableHTML([
                    {key:"product_name",label:"Product"},
                    {key:"units_sold",label:"Units Sold"}
                ],fast)}</tbody></table></div>
            </div></div>
            <div class="col-12"><div class="content-card">
                <h6>Supplier Performance</h6>
                <div class="table-responsive"><table class="table">
                <thead><tr><th>Supplier</th><th>Total Orders</th>
                <th>Received Orders</th><th>Purchase Value</th></tr></thead>
                <tbody>${tableHTML([
                    {key:"supplier_name",label:"Supplier"},
                    {key:"total_orders",label:"Total Orders"},
                    {key:"received_orders",label:"Received Orders"},
                    {key:"received_purchase_value",label:"Purchase Value",money:true}
                ],supplierRows)}</tbody></table></div>
            </div></div>
        </div>
    `;

    new Chart(document.getElementById("reportValuationChart"),{
        type:"doughnut",
        data:{
            labels:warehouseRows.map(w=>w.warehouse_name),
            datasets:[{data:warehouseRows.map(w=>Number(w.inventory_value))}]
        },
        options:{responsive:true}
    });

    new Chart(document.getElementById("reportRevenueChart"),{
        type:"bar",
        data:{
            labels:warehouseRows.map(w=>w.warehouse_name),
            datasets:[{label:"Revenue",data:warehouseRows.map(w=>Number(w.completed_revenue))}]
        },
        options:{responsive:true}
    });

    new Chart(document.getElementById("monthlySalesChart"),{
        type:"line",
        data:{
            labels:monthlyRows.map(m=>m.month),
            datasets:[{label:"Revenue",data:monthlyRows.map(m=>Number(m.revenue)),tension:.3}]
        },
        options:{responsive:true}
    });
}
