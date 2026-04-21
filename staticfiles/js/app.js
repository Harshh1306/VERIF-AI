document.addEventListener("DOMContentLoaded", () => {
    const analysisForm = document.querySelector("[data-analysis-form]");
    const overlay = document.getElementById("analysisOverlay");

    if (analysisForm && overlay) {
        analysisForm.addEventListener("submit", () => {
            overlay.classList.add("is-visible");
            overlay.setAttribute("aria-hidden", "false");
        });
    }

    const fileInput = document.querySelector("#id_uploaded_file");
    const fileTypeInput = document.querySelector("#id_file_type");
    const previewMedia = document.querySelector("[data-preview-media]");
    const fileName = document.querySelector("[data-file-name]");
    const fileDetails = document.querySelector("[data-file-details]");

    function renderPreview() {
        if (!fileInput || !previewMedia || !fileInput.files.length) {
            return;
        }

        const file = fileInput.files[0];
        const fileUrl = URL.createObjectURL(file);
        const extension = file.name.includes(".") ? file.name.split(".").pop().toUpperCase() : "FILE";
        const sizeInMb = (file.size / (1024 * 1024)).toFixed(2);
        let mode = fileTypeInput ? fileTypeInput.value : "";

        if (fileTypeInput) {
            if (file.type.startsWith("video/")) {
                fileTypeInput.value = "video";
                mode = "video";
            } else if (file.type.startsWith("image/")) {
                fileTypeInput.value = "image";
                mode = "image";
            }
        }

        if (fileName) {
            fileName.textContent = file.name;
        }
        if (fileDetails) {
            fileDetails.textContent = `${extension} • ${sizeInMb} MB`;
        }

        if (mode === "video" || file.type.startsWith("video/")) {
            previewMedia.innerHTML = `<video class="preview-media" controls preload="metadata"><source src="${fileUrl}" type="${file.type}"></video>`;
        } else if (file.type.startsWith("image/")) {
            previewMedia.innerHTML = `<img class="preview-media" src="${fileUrl}" alt="Selected file preview">`;
        } else {
            previewMedia.innerHTML = `
                <div class="preview-card__empty">
                    <span class="preview-card__icon">${extension.slice(0, 1)}</span>
                    <p>Preview unavailable for this file type, but it is ready for analysis.</p>
                </div>
            `;
        }
    }

    if (fileInput) {
        fileInput.addEventListener("change", renderPreview);
    }
    if (fileTypeInput) {
        fileTypeInput.addEventListener("change", renderPreview);
    }
});
