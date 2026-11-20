function escapeProductHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

async function loadProductsPage() {
    pageContent.innerHTML = `
        <div class="page-heading">
            <div>
                <h3>Product Management</h3>
                <p>Manage your products, prices and stock reorder levels.</p>
            </div>
            <button class="btn btn-primary" id="addProductBtn">
                <i class="bi bi-plus-lg"></i> Add Product
            </button>
        </div>

        <div class="row g-3 mb-3" id="productStats"></div>

        <div class="content-card">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
                <h6 class="mb-0">Product Catalogue</h6>
                <div class="d-flex gap-2 flex-wrap">
                    <input type="search" id="productSearch"
                        class="form-control search-input"
                        placeholder="Search name or SKU...">

                    <select id="categoryFilter" class="form-select"
                        style="min-width:160px">
                        <option value="">All Categories</option>
                    </select>

                    <button class="btn btn-outline-primary" id="refreshProducts">
                        <i class="bi bi-arrow-clockwise"></i>
                    </button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>SKU</th>
                            <th>Product</th>
                            <th>Category</th>
                            <th>Unit Price</th>
                            <th>Reorder Level</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="productsTableBody">
                        <tr><td colspan="7" class="text-center">Loading...</td></tr>
                    </tbody>
                </table>
            </div>

            <div class="text-muted small" id="productCount"></div>
        </div>

        <div id="productModal" class="product-modal d-none">
            <div class="product-modal-card">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5 id="productModalTitle">Add Product</h5>
                    <button class="btn-close" id="closeProductModal"></button>
                </div>

                <form id="productForm">
                    <input type="hidden" id="productId">

                    <div class="mb-3">
                        <label class="form-label">Product Name *</label>
                        <input type="text" class="form-control"
                            id="productName" required maxlength="150">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">SKU *</label>
                        <input type="text" class="form-control"
                            id="productSKU" required maxlength="50">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Category *</label>
                        <select class="form-select" id="productCategory" required>
                            <option value="">Select category</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Description</label>
                        <textarea class="form-control" id="productDescription"
                            rows="2" maxlength="500"></textarea>
                    </div>

                    <div class="row">
                        <div class="col-6 mb-3">
                            <label class="form-label">Unit Price (₹) *</label>
                            <input type="number" class="form-control"
                                id="productPrice" min="0.01" step="0.01" required>
                        </div>

                        <div class="col-6 mb-3">
                            <label class="form-label">Reorder Level *</label>
                            <input type="number" class="form-control"
                                id="productReorder" min="0" step="1" required>
                        </div>
                    </div>

                    <div id="productFormError"
                        class="alert alert-danger d-none"></div>

                    <div class="d-flex justify-content-end gap-2 mt-3">
                        <button type="button" class="btn btn-light"
                            id="cancelProductModal">Cancel</button>

                        <button type="submit" class="btn btn-primary"
                            id="saveProductBtn">Save Product</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    const [firstProductResponse, categoryResponse] = await Promise.all([
    API.get("/products/?page=1"),
    API.get("/categories/")
]);

// Collect products from every available page
window.stockProducts = [...(firstProductResponse.data || [])];

const totalPages = firstProductResponse.pagination?.total_pages || 1;

for (let page = 2; page <= totalPages; page++) {
    const response = await API.get(`/products/?page=${page}`);
    window.stockProducts.push(...(response.data || []));
}

window.stockCategories = categoryResponse.data || [];

    const canManage = ["Admin", "Manager"].includes(user.role);
    const isAdmin = user.role === "Admin";

    document.getElementById("addProductBtn").style.display =
        canManage ? "" : "none";

    const categoryOptions = window.stockCategories.map(category => `
        <option value="${category.category_id}">
            ${escapeProductHTML(category.category_name)}
        </option>
    `).join("");

    document.getElementById("categoryFilter").innerHTML += categoryOptions;
    document.getElementById("productCategory").innerHTML += categoryOptions;

    renderProductsTable();

    document.getElementById("productSearch").addEventListener("input",
        renderProductsTable);

    document.getElementById("categoryFilter").addEventListener("change",
        renderProductsTable);

    document.getElementById("refreshProducts").addEventListener("click",
        () => loadPage("products"));

    document.getElementById("addProductBtn").addEventListener("click",
        () => openProductModal());

    document.getElementById("closeProductModal").addEventListener("click",
        closeProductModal);

    document.getElementById("cancelProductModal").addEventListener("click",
        closeProductModal);

    document.getElementById("productForm").addEventListener("submit",
        saveProduct);

    document.getElementById("productsTableBody").addEventListener("click",
        async event => {
            const button = event.target.closest("button[data-action]");
            if (!button) return;

            const id = Number(button.dataset.id);
            const product = window.stockProducts.find(
                item => Number(item.product_id) === id
            );

            if (!product) return;

            if (button.dataset.action === "edit") {
                openProductModal(product);
            }

            if (button.dataset.action === "delete") {
                await deleteProduct(product);
            }
        });
}


function renderProductsTable() {
    const search = document.getElementById("productSearch").value
        .trim().toLowerCase();

    const category = document.getElementById("categoryFilter").value;

    const filtered = window.stockProducts.filter(product => {
        const matchesSearch =
            String(product.product_name || "").toLowerCase().includes(search) ||
            String(product.sku || "").toLowerCase().includes(search);

        const matchesCategory =
            !category || String(product.category_id) === category;

        return matchesSearch && matchesCategory;
    });

    const tbody = document.getElementById("productsTableBody");

    const canManage = ["Admin", "Manager"].includes(user.role);
    const isAdmin = user.role === "Admin";

    if (!filtered.length) {
        tbody.innerHTML = `
            <tr><td colspan="7" class="text-center py-4">
                No products found.
            </td></tr>
        `;
    } else {
        tbody.innerHTML = filtered.map(product => `
            <tr>
                <td>${product.product_id}</td>
                <td><span class="badge bg-light text-dark">
                    ${escapeProductHTML(product.sku)}
                </span></td>
                <td>
                    <strong>${escapeProductHTML(product.product_name)}</strong>
                </td>
                <td>${escapeProductHTML(product.category_name || "-")}</td>
                <td>${money(product.unit_price)}</td>
                <td>${product.reorder_level}</td>
                <td>
                    ${canManage ? `
                        <button class="action-button"
                            data-action="edit"
                            data-id="${product.product_id}"
                            title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                    ` : ""}

                    ${isAdmin ? `
                        <button class="action-button text-danger"
                            data-action="delete"
                            data-id="${product.product_id}"
                            title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    ` : ""}
                </td>
            </tr>
        `).join("");
    }

    document.getElementById("productCount").textContent =
        `Showing ${filtered.length} of ${window.stockProducts.length} products`;

    document.getElementById("productStats").innerHTML = `
        <div class="col-md-4">
            <div class="stat-card">
                <div>
                    <p>Total Products</p>
                    <h3>${window.stockProducts.length}</h3>
                </div>
                <div class="stat-icon"><i class="bi bi-box"></i></div>
            </div>
        </div>

        <div class="col-md-4">
            <div class="stat-card">
                <div>
                    <p>Categories</p>
                    <h3>${window.stockCategories.length}</h3>
                </div>
                <div class="stat-icon"><i class="bi bi-tags"></i></div>
            </div>
        </div>

        <div class="col-md-4">
            <div class="stat-card">
                <div>
                    <p>Average Product Price</p>
                    <h3>${money(
                        window.stockProducts.length
                            ? window.stockProducts.reduce(
                                (sum, p) => sum + Number(p.unit_price || 0), 0
                            ) / window.stockProducts.length
                            : 0
                    )}</h3>
                </div>
                <div class="stat-icon"><i class="bi bi-currency-rupee"></i></div>
            </div>
        </div>
    `;
}


function openProductModal(product = null) {
    const modal = document.getElementById("productModal");
    const form = document.getElementById("productForm");

    form.reset();

    document.getElementById("productId").value =
        product ? product.product_id : "";

    document.getElementById("productModalTitle").textContent =
        product ? "Edit Product" : "Add New Product";

    document.getElementById("productName").value =
        product?.product_name || "";

    document.getElementById("productSKU").value =
        product?.sku || "";

    document.getElementById("productCategory").value =
        product?.category_id || "";

    document.getElementById("productDescription").value =
        product?.description || "";

    document.getElementById("productPrice").value =
        product?.unit_price ?? "";

    document.getElementById("productReorder").value =
        product?.reorder_level ?? 10;

    document.getElementById("productFormError").classList.add("d-none");

    modal.classList.remove("d-none");
}


function closeProductModal() {
    document.getElementById("productModal").classList.add("d-none");
}


async function saveProduct(event) {
    event.preventDefault();

    const id = document.getElementById("productId").value;

    const payload = {
        product_name: document.getElementById("productName").value.trim(),
        sku: document.getElementById("productSKU").value.trim(),
        category_id: Number(document.getElementById("productCategory").value),
        description: document.getElementById("productDescription").value.trim(),
        unit_price: Number(document.getElementById("productPrice").value),
        reorder_level: Number(document.getElementById("productReorder").value)
    };

    const button = document.getElementById("saveProductBtn");
    const errorBox = document.getElementById("productFormError");

    if (!payload.product_name || !payload.sku || !payload.category_id ||
        !Number.isFinite(payload.unit_price) || payload.unit_price <= 0 ||
        !Number.isInteger(payload.reorder_level) || payload.reorder_level < 0) {

        errorBox.textContent = "Please enter valid values in all required fields.";
        errorBox.classList.remove("d-none");
        return;
    }

    button.disabled = true;
    button.textContent = "Saving...";

    errorBox.classList.add("d-none");

    try {
        if (id) {
            await API.put(`/products/${id}`, payload);
        } else {
            await API.post("/products/", payload);
        }

        closeProductModal();
        await loadPage("products");

    } catch (error) {
        errorBox.textContent = error.message;
        errorBox.classList.remove("d-none");
    } finally {
        button.disabled = false;
        button.textContent = "Save Product";
    }
}


async function deleteProduct(product) {
    const confirmed = confirm(
        `Delete "${product.product_name}"?\n\nThis action cannot be undone.`
    );

    if (!confirmed) return;

    try {
        await API.delete(`/products/${product.product_id}`);
        alert("Product deleted successfully.");
        await loadPage("products");
    } catch (error) {
        alert(`Unable to delete product: ${error.message}`);
    }
}
