function escapeCategoryHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

async function loadCategoriesPage() {

    pageContent.innerHTML = `
        <div class="page-heading">
            <div>
                <h3>Category Management</h3>
                <p>Organise products into categories.</p>
            </div>
            <button class="btn btn-primary" id="addCategoryBtn">
                <i class="bi bi-plus-lg"></i> Add Category
            </button>
        </div>

        <div class="row g-3 mb-4" id="categoryStats"></div>

        <div class="content-card">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
                <h6 class="mb-0">Category List</h6>

                <div class="d-flex gap-2">
                    <input type="search" id="categorySearch"
                        class="form-control search-input"
                        placeholder="Search categories...">

                    <button class="btn btn-outline-primary" id="refreshCategories">
                        <i class="bi bi-arrow-clockwise"></i>
                    </button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Category Name</th>
                            <th>Description</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="categoriesTableBody">
                        <tr><td colspan="4" class="text-center">Loading...</td></tr>
                    </tbody>
                </table>
            </div>

            <div class="text-muted small" id="categoryCount"></div>
        </div>

        <div id="categoryModal" class="product-modal d-none">
            <div class="product-modal-card">

                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5 id="categoryModalTitle">Add Category</h5>
                    <button class="btn-close" id="closeCategoryModal"></button>
                </div>

                <form id="categoryForm">
                    <input type="hidden" id="categoryId">

                    <div class="mb-3">
                        <label class="form-label">Category Name *</label>
                        <input type="text" class="form-control"
                            id="categoryName" required maxlength="100"
                            placeholder="Enter category name">
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Description</label>
                        <textarea class="form-control" id="categoryDescription"
                            rows="4" maxlength="500"
                            placeholder="Describe this category"></textarea>
                    </div>

                    <div id="categoryFormError"
                        class="alert alert-danger d-none"></div>

                    <div class="d-flex justify-content-end gap-2 mt-3">
                        <button type="button" class="btn btn-light"
                            id="cancelCategoryModal">Cancel</button>

                        <button type="submit" class="btn btn-primary"
                            id="saveCategoryBtn">Save Category</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    const response = await API.get("/categories/");
    window.stockCategories = response.data || [];

    document.getElementById("addCategoryBtn").style.display =
        ["Admin", "Manager"].includes(user.role) ? "" : "none";

    renderCategoriesTable();

    document.getElementById("categorySearch").addEventListener(
        "input", renderCategoriesTable
    );

    document.getElementById("refreshCategories").addEventListener(
        "click", () => loadPage("categories")
    );

    document.getElementById("addCategoryBtn").addEventListener(
        "click", () => openCategoryModal()
    );

    document.getElementById("closeCategoryModal").addEventListener(
        "click", closeCategoryModal
    );

    document.getElementById("cancelCategoryModal").addEventListener(
        "click", closeCategoryModal
    );

    document.getElementById("categoryForm").addEventListener(
        "submit", saveCategory
    );

    document.getElementById("categoriesTableBody").addEventListener(
        "click", async event => {

            const button = event.target.closest("button[data-action]");
            if (!button) return;

            const id = Number(button.dataset.id);

            const category = window.stockCategories.find(
                item => Number(item.category_id) === id
            );

            if (!category) return;

            if (button.dataset.action === "edit") {
                openCategoryModal(category);
            }

            if (button.dataset.action === "delete") {
                await deleteCategory(category);
            }
        }
    );
}


function renderCategoriesTable() {

    const search = document.getElementById("categorySearch")
        .value.trim().toLowerCase();

    const filtered = window.stockCategories.filter(category =>
        String(category.category_name || "").toLowerCase().includes(search) ||
        String(category.description || "").toLowerCase().includes(search)
    );

    const canManage = ["Admin", "Manager"].includes(user.role);
    const isAdmin = user.role === "Admin";

    const tbody = document.getElementById("categoriesTableBody");

    if (!filtered.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center py-4">
                    No categories found.
                </td>
            </tr>
        `;
    } else {

        tbody.innerHTML = filtered.map(category => `
            <tr>
                <td>${category.category_id}</td>
                <td>
                    <strong>${escapeCategoryHTML(category.category_name)}</strong>
                </td>
                <td>${escapeCategoryHTML(category.description || "-")}</td>
                <td>
                    ${canManage ? `
                        <button class="action-button"
                            data-action="edit"
                            data-id="${category.category_id}"
                            title="Edit category">
                            <i class="bi bi-pencil"></i>
                        </button>
                    ` : ""}

                    ${isAdmin ? `
                        <button class="action-button text-danger"
                            data-action="delete"
                            data-id="${category.category_id}"
                            title="Delete category">
                            <i class="bi bi-trash"></i>
                        </button>
                    ` : ""}
                </td>
            </tr>
        `).join("");
    }

    document.getElementById("categoryCount").textContent =
        `Showing ${filtered.length} of ${window.stockCategories.length} categories`;

    document.getElementById("categoryStats").innerHTML = `
        <div class="col-md-6">
            <div class="stat-card">
                <div>
                    <p>Total Categories</p>
                    <h3>${window.stockCategories.length}</h3>
                    <small class="text-muted">Registered categories</small>
                </div>
                <div class="stat-icon"><i class="bi bi-tags"></i></div>
            </div>
        </div>

        <div class="col-md-6">
            <div class="stat-card">
                <div>
                    <p>Categories With Descriptions</p>
                    <h3>${window.stockCategories.filter(
                        category => String(category.description || "").trim()
                    ).length}</h3>
                    <small class="text-muted">Documented categories</small>
                </div>
                <div class="stat-icon"><i class="bi bi-card-text"></i></div>
            </div>
        </div>
    `;
}


function openCategoryModal(category = null) {

    document.getElementById("categoryForm").reset();

    document.getElementById("categoryId").value =
        category ? category.category_id : "";

    document.getElementById("categoryName").value =
        category?.category_name || "";

    document.getElementById("categoryDescription").value =
        category?.description || "";

    document.getElementById("categoryModalTitle").textContent =
        category ? "Edit Category" : "Add New Category";

    document.getElementById("categoryFormError").classList.add("d-none");

    document.getElementById("categoryModal").classList.remove("d-none");
}


function closeCategoryModal() {
    document.getElementById("categoryModal").classList.add("d-none");
}


async function saveCategory(event) {

    event.preventDefault();

    const id = document.getElementById("categoryId").value;

    const payload = {
        category_name: document.getElementById("categoryName").value.trim(),
        description: document.getElementById("categoryDescription").value.trim()
    };

    const button = document.getElementById("saveCategoryBtn");
    const errorBox = document.getElementById("categoryFormError");

    if (!payload.category_name) {
        errorBox.textContent = "Category name is required.";
        errorBox.classList.remove("d-none");
        return;
    }

    button.disabled = true;
    button.textContent = "Saving...";
    errorBox.classList.add("d-none");

    try {

        if (id) {
            await API.put(`/categories/${id}`, payload);
        } else {
            await API.post("/categories/", payload);
        }

        closeCategoryModal();
        await loadPage("categories");

    } catch (error) {

        errorBox.textContent = error.message;
        errorBox.classList.remove("d-none");

    } finally {

        button.disabled = false;
        button.textContent = "Save Category";

    }
}


async function deleteCategory(category) {

    const confirmed = confirm(
        `Delete category "${category.category_name}"?\n\n` +
        "The database may reject deletion if products are linked to it."
    );

    if (!confirmed) return;

    try {

        await API.delete(`/categories/${category.category_id}`);

        alert("Category deleted successfully.");

        await loadPage("categories");

    } catch (error) {

        alert(`Unable to delete category: ${error.message}`);

    }
}
