if (localStorage.getItem("stockmaster_token")) {
    window.location.href = "index.html";
}

const loginForm = document.getElementById("loginForm");

document.getElementById("togglePassword").addEventListener("click", () => {
    const input = document.getElementById("password");
    input.type = input.type === "password" ? "text" : "password";
});

loginForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    const button = document.getElementById("loginButton");
    const errorBox = document.getElementById("loginError");

    button.disabled = true;
    button.innerHTML = "Signing in...";

    errorBox.classList.add("d-none");

    try {

        const response = await API.post("/auth/login", {
            email,
            password
        });

        localStorage.setItem("stockmaster_token", response.token);
        localStorage.setItem("stockmaster_user", JSON.stringify(response.user));

        window.location.href = "index.html";

    } catch (error) {

        errorBox.textContent = error.message;
        errorBox.classList.remove("d-none");

    } finally {

        button.disabled = false;
        button.innerHTML = 'Sign In <i class="bi bi-arrow-right ms-2"></i>';

    }

});
