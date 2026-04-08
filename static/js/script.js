console.log("FaceTrace Loaded");

// Sidebar toggle
document.getElementById("menu-btn")?.addEventListener("click", function () {
    document.getElementById("sidebar").classList.toggle("active");
});

// Close sidebar on click
document.querySelectorAll("#sidebar a").forEach(link => {
    link.addEventListener("click", () => {
        document.getElementById("sidebar").classList.remove("active");
    });
});

// Confirm action
function confirmAction(action) {
    return confirm("Are you sure you want to " + action + "?");
}

// Image preview
function previewImage(input) {
    const preview = document.getElementById("preview");
    const file = input.files[0];

    if (file) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
    }
}
