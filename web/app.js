const CATEGORY_LABELS = {
    All: "הכול",
    Recipe: "מתכונים",
    Travel: "טיולים",
    Document: "מסמכים",
    Purchase: "קניות",
    Recommendation: "המלצות",
    Finance: "כספים",
    Other: "אחר",
};

const CATEGORY_ORDER = [
    "All",
    "Recipe",
    "Travel",
    "Document",
    "Purchase",
    "Recommendation",
    "Finance",
    "Other",
];

const SOURCE_LABELS = {
    text: "טקסט",
    url: "קישור",
    image: "תמונה",
};

const SOURCE_ICONS = {
    text: "✦",
    url: "↗",
    image: "▣",
};


let allItems = [];
let selectedCategory = "All";
let searchTerm = "";


/* =========================
   DOM
========================== */

const itemsGrid = document.getElementById("itemsGrid");
const itemCount = document.getElementById("itemCount");

const categoryFilters = document.getElementById(
    "categoryFilters"
);

const searchInput = document.getElementById(
    "searchInput"
);

const clearSearch = document.getElementById(
    "clearSearch"
);

const emptyState = document.getElementById(
    "emptyState"
);

const resetFilters = document.getElementById(
    "resetFilters"
);

const resultsDescription = document.getElementById(
    "resultsDescription"
);

const itemModal = document.getElementById(
    "itemModal"
);

const modalOverlay = document.getElementById(
    "modalOverlay"
);

const modalClose = document.getElementById(
    "modalClose"
);

const modalContent = document.getElementById(
    "modalContent"
);


/* =========================
   INITIAL LOAD
========================== */

async function loadItems() {
    try {
        const response = await fetch(
            "/static/mock_items.json"
        );

        if (!response.ok) {
            throw new Error(
                `Could not load items: ${response.status}`
            );
        }

        allItems = await response.json();

        sortItemsNewestFirst();

        itemCount.textContent = allItems.length;

        renderCategoryFilters();
        renderItems();
    } catch (error) {
        console.error(error);

        itemsGrid.innerHTML = `
            <div class="empty-state">
                <h3>לא הצלחנו לטעון את הפריטים</h3>
                <p>
                    ודאי שהשרת פועל ושקובץ
                    mock_items.json נמצא בתיקיית web.
                </p>
            </div>
        `;
    }
}


function sortItemsNewestFirst() {
    allItems.sort((a, b) => {
        const dateA = new Date(a.created_at || 0);
        const dateB = new Date(b.created_at || 0);

        return dateB - dateA;
    });
}


/* =========================
   CATEGORY FILTERS
========================== */

function renderCategoryFilters() {
    categoryFilters.innerHTML = "";

    CATEGORY_ORDER.forEach((category) => {
        const button = document.createElement("button");

        button.type = "button";
        button.className = "category-button";

        if (category === selectedCategory) {
            button.classList.add("active");
        }

        const count = getCategoryCount(category);

        button.textContent =
            `${CATEGORY_LABELS[category]} · ${count}`;

        button.addEventListener("click", () => {
            selectedCategory = category;

            renderCategoryFilters();
            renderItems();
        });

        categoryFilters.appendChild(button);
    });
}


function getCategoryCount(category) {
    if (category === "All") {
        return allItems.length;
    }

    return allItems.filter(
        (item) => item.category === category
    ).length;
}


/* =========================
   FILTERING
========================== */

function getFilteredItems() {
    const normalizedSearch = normalizeText(
        searchTerm
    );

    return allItems.filter((item) => {
        const matchesCategory =
            selectedCategory === "All" ||
            item.category === selectedCategory;

        if (!matchesCategory) {
            return false;
        }

        if (!normalizedSearch) {
            return true;
        }

        const searchableParts = [
            item.title,
            item.summary,
            item.category,
            ...(item.tags || []),
            item.original_text,
            item.original_url,
            item.image_description,
            item.extracted_text,
        ];

        const searchableText = normalizeText(
            searchableParts
                .filter(Boolean)
                .join(" ")
        );

        return searchableText.includes(
            normalizedSearch
        );
    });
}


function normalizeText(value) {
    return String(value || "")
        .toLowerCase()
        .trim();
}


/* =========================
   ITEMS
========================== */

function renderItems() {
    const items = getFilteredItems();

    itemsGrid.innerHTML = "";

    emptyState.hidden = items.length !== 0;

    updateResultsDescription(items.length);

    items.forEach((item) => {
        itemsGrid.appendChild(
            createItemCard(item)
        );
    });
}


function createItemCard(item) {
    const article = document.createElement("article");

    article.className = "memory-card";

    const button = document.createElement("button");

    button.type = "button";
    button.className = "memory-card-button";

    button.addEventListener("click", () => {
        openItemModal(item);
    });

    if (item.source_type === "image") {
        button.appendChild(
            createImagePreview(item)
        );
    }

    const content = document.createElement("div");

    content.className = "card-content";


    const topRow = document.createElement("div");

    topRow.className = "card-top-row";


    const sourceBadge = document.createElement("span");

    sourceBadge.className = "source-badge";

    sourceBadge.textContent =
        `${SOURCE_ICONS[item.source_type] || "•"} ` +
        `${SOURCE_LABELS[item.source_type] || "פריט"}`;


    const categoryLabel = document.createElement("span");

    categoryLabel.className = "category-label";

    categoryLabel.textContent =
        CATEGORY_LABELS[item.category] ||
        item.category ||
        "אחר";


    topRow.append(
        sourceBadge,
        categoryLabel
    );


    const title = document.createElement("h3");

    title.className = "card-title";

    title.textContent =
        item.title || "פריט ללא כותרת";


    const summary = document.createElement("p");

    summary.className = "card-summary";

    summary.textContent =
        item.summary || "אין תקציר לפריט הזה.";


    const footer = document.createElement("div");

    footer.className = "card-footer";


    const tags = createTags(item.tags || []);

    const date = document.createElement("div");

    date.className = "card-date";

    date.textContent = formatDate(
        item.created_at
    );


    footer.append(
        tags,
        date
    );


    content.append(
        topRow,
        title,
        summary,
        footer
    );

    button.appendChild(content);

    article.appendChild(button);

    return article;
}


/* =========================
   IMAGE PREVIEW
========================== */

function createImagePreview(item) {
    const visual = document.createElement("div");

    visual.className = "card-image";

    if (item.image_url) {
        const image = document.createElement("img");

        image.src = item.image_url;
        image.alt = item.title || "תמונה שמורה";

        image.addEventListener("error", () => {
            visual.innerHTML = "";

            visual.appendChild(
                createImagePlaceholder()
            );
        });

        visual.appendChild(image);
    } else {
        visual.appendChild(
            createImagePlaceholder()
        );
    }

    return visual;
}


function createImagePlaceholder() {
    const placeholder =
        document.createElement("div");

    placeholder.className =
        "card-image-placeholder";

    placeholder.textContent = "▣";

    return placeholder;
}


/* =========================
   TAGS
========================== */

function createTags(tags) {
    const container = document.createElement("div");

    container.className = "tags";

    tags.slice(0, 3).forEach((tagText) => {
        const tag = document.createElement("span");

        tag.className = "tag";
        tag.textContent = `#${tagText}`;

        container.appendChild(tag);
    });

    return container;
}


/* =========================
   MODAL
========================== */

function openItemModal(item) {
    modalContent.innerHTML = "";

    if (item.source_type === "image") {
        modalContent.appendChild(
            createModalVisual(item)
        );
    }


    const meta = document.createElement("div");

    meta.className = "modal-meta";


    const sourceBadge = document.createElement("span");

    sourceBadge.className = "source-badge";

    sourceBadge.textContent =
        `${SOURCE_ICONS[item.source_type] || "•"} ` +
        `${SOURCE_LABELS[item.source_type] || "פריט"}`;


    const category = document.createElement("span");

    category.className = "category-label";

    category.textContent =
        CATEGORY_LABELS[item.category] ||
        item.category ||
        "אחר";


    meta.append(
        sourceBadge,
        category
    );


    const title = document.createElement("h2");

    title.id = "modalTitle";
    title.className = "modal-title";

    title.textContent =
        item.title || "פריט ללא כותרת";


    const summary = document.createElement("p");

    summary.className = "modal-summary";

    summary.textContent =
        item.summary || "אין תקציר לפריט הזה.";


    modalContent.append(
        meta,
        title,
        summary
    );


    if (item.tags?.length) {
        const tagSection = createModalSection(
            "תגיות"
        );

        tagSection.appendChild(
            createTags(item.tags)
        );

        modalContent.appendChild(
            tagSection
        );
    }


    if (item.original_text) {
        modalContent.appendChild(
            createTextSection(
                "תוכן",
                item.original_text
            )
        );
    }


    if (item.image_description) {
        modalContent.appendChild(
            createTextSection(
                "תיאור התמונה",
                item.image_description
            )
        );
    }


    if (item.extracted_text) {
        modalContent.appendChild(
            createTextSection(
                "טקסט שזוהה בתמונה",
                item.extracted_text
            )
        );
    }


    if (item.original_url) {
        modalContent.appendChild(
            createLinkSection(
                item.original_url
            )
        );
    }


    const dateSection = createTextSection(
        "נשמר בתאריך",
        formatDateTime(item.created_at)
    );

    modalContent.appendChild(dateSection);


    itemModal.classList.add("open");

    itemModal.setAttribute(
        "aria-hidden",
        "false"
    );

    document.body.style.overflow = "hidden";

    modalClose.focus();
}


function createModalVisual(item) {
    const visual = document.createElement("div");

    visual.className = "modal-visual";

    if (item.image_url) {
        const image = document.createElement("img");

        image.src = item.image_url;
        image.alt = item.title || "תמונה שמורה";

        image.addEventListener("error", () => {
            visual.innerHTML = "";

            visual.appendChild(
                createModalPlaceholder()
            );
        });

        visual.appendChild(image);
    } else {
        visual.appendChild(
            createModalPlaceholder()
        );
    }

    return visual;
}


function createModalPlaceholder() {
    const placeholder =
        document.createElement("div");

    placeholder.className =
        "modal-placeholder";

    placeholder.textContent = "▣";

    return placeholder;
}


function createModalSection(title) {
    const section = document.createElement("section");

    section.className = "modal-section";

    const heading = document.createElement("h4");

    heading.textContent = title;

    section.appendChild(heading);

    return section;
}


function createTextSection(title, text) {
    const section = createModalSection(title);

    const paragraph = document.createElement("p");

    paragraph.textContent = text;

    section.appendChild(paragraph);

    return section;
}


function createLinkSection(url) {
    const section = createModalSection(
        "קישור שמור"
    );

    const link = document.createElement("a");

    link.className = "modal-link";
    link.textContent = "פתיחת הקישור ↗";

    link.href = getSafeUrl(url);

    link.target = "_blank";
    link.rel = "noopener noreferrer";

    section.appendChild(link);

    return section;
}


function closeModal() {
    itemModal.classList.remove("open");

    itemModal.setAttribute(
        "aria-hidden",
        "true"
    );

    document.body.style.overflow = "";
}


/* =========================
   RESULTS DESCRIPTION
========================== */

function updateResultsDescription(count) {
    if (
        selectedCategory === "All" &&
        !searchTerm
    ) {
        resultsDescription.textContent =
            `מציג ${count} פריטים שמורים`;

        return;
    }

    if (count === 0) {
        resultsDescription.textContent =
            "לא נמצאו פריטים מתאימים";

        return;
    }

    resultsDescription.textContent =
        `נמצאו ${count} פריטים`;
}


/* =========================
   DATE HELPERS
========================== */

function formatDate(value) {
    if (!value) {
        return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return new Intl.DateTimeFormat(
        "he-IL",
        {
            day: "numeric",
            month: "short",
            year: "numeric",
        }
    ).format(date);
}


function formatDateTime(value) {
    if (!value) {
        return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return new Intl.DateTimeFormat(
        "he-IL",
        {
            day: "numeric",
            month: "long",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        }
    ).format(date);
}


/* =========================
   URL SAFETY
========================== */

function getSafeUrl(value) {
    try {
        const url = new URL(value);

        if (
            url.protocol === "http:" ||
            url.protocol === "https:"
        ) {
            return url.href;
        }
    } catch {
        // Invalid URL.
    }

    return "#";
}


/* =========================
   EVENTS
========================== */

searchInput.addEventListener(
    "input",
    (event) => {
        searchTerm = event.target.value;

        clearSearch.hidden =
            searchTerm.length === 0;

        renderItems();
    }
);


clearSearch.addEventListener(
    "click",
    () => {
        searchTerm = "";

        searchInput.value = "";
        clearSearch.hidden = true;

        renderItems();

        searchInput.focus();
    }
);


resetFilters.addEventListener(
    "click",
    () => {
        selectedCategory = "All";
        searchTerm = "";

        searchInput.value = "";
        clearSearch.hidden = true;

        renderCategoryFilters();
        renderItems();
    }
);


modalClose.addEventListener(
    "click",
    closeModal
);


modalOverlay.addEventListener(
    "click",
    closeModal
);


document.addEventListener(
    "keydown",
    (event) => {
        if (
            event.key === "Escape" &&
            itemModal.classList.contains("open")
        ) {
            closeModal();
        }
    }
);


/* =========================
   START
========================== */

loadItems();