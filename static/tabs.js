// tabs.js
document.addEventListener("DOMContentLoaded", function () {
    const tabButtons = document.querySelectorAll(".tab-button");
    const tabContents = document.querySelectorAll(".tab-content");

    tabButtons.forEach(button => {
        button.addEventListener("click", (e) => {
            e.preventDefault(); // Prevent the default anchor behavior

            // Remove the active class from all buttons and content sections
            tabButtons.forEach(btn => btn.classList.remove("active"));
            tabContents.forEach(content => content.classList.remove("active"));

            // Add active class to the clicked button
            button.classList.add("active");

            // Display the corresponding content section
            const targetId = button.getAttribute("href").substring(1);
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                targetContent.classList.add("active");
            }
        });
    });
});
