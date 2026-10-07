// ========================================
// MANAS LINK HUB — ANALYTICS
// V2.0
// Local + Python Backend Tracking
// ========================================

const ANALYTICS_API = "/api/event";

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        console.log(
            "Manas Link Hub Analytics loaded."
        );


        // ----------------------------------------
        // RECORD PAGE VISIT
        // ----------------------------------------

        sendEventToBackend(
            "visit",
            null
        );


        // ----------------------------------------
        // LOAD MANAGED PUBLIC LINKS
        // ----------------------------------------

        await loadPublicLinks();


        // ----------------------------------------
        // TRACK STATIC / FALLBACK LINKS
        // ----------------------------------------

        bindTrackedLinks();

    }
);


// ========================================
// LOAD PUBLIC LINKS
// ========================================

async function loadPublicLinks() {

    try {

        const response =
            await fetch(
                "/api/public-links"
            );


        if (!response.ok) {

            throw new Error(
                `Public links request failed: ${response.status}`
            );

        }


        const result =
            await response.json();


        if (
            !result.success ||
            !Array.isArray(result.links)
        ) {

            throw new Error(
                "Invalid public links response."
            );

        }


        renderPublicLinks(
            result.links
        );


        console.log(
            `Loaded ${result.links.length} managed links.`
        );


    } catch (error) {

        // Keep the original HTML as fallback.
        console.warn(
            "Could not load managed links:",
            error.message
        );

    }

}


// ========================================
// ESCAPE HTML
// ========================================

function escapeHtml(value) {

    return String(
        value ?? ""
    )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}

// ========================================
// AUTOMATIC PUBLIC LINK ICON
// ========================================

function getPublicLinkIcon(url) {

    try {

        const hostname =
            new URL(url)
                .hostname
                .toLowerCase();

        if (
            hostname.includes("github.com")
        ) {
            return "GH";
        }

        if (
            hostname.includes("instagram.com")
        ) {
            return "IG";
        }

        if (
            hostname.includes("linkedin.com")
        ) {
            return "in";
        }

        if (
            hostname.includes("youtube.com") ||
            hostname.includes("youtu.be")
        ) {
            return "YT";
        }

        if (
            hostname === "x.com" ||
            hostname.includes("twitter.com")
        ) {
            return "X";
        }

        if (
            hostname.includes("discord.com") ||
            hostname.includes("discord.gg")
        ) {
            return "DC";
        }

        if (
            hostname.includes("facebook.com")
        ) {
            return "f";
        }

        if (
            hostname.includes("t.me") ||
            hostname.includes("telegram.me") ||
            hostname.includes("telegram.org")
        ) {
            return "TG";
        }

        return "↗";

    } catch {

        return "↗";

    }

}

// ========================================
// RENDER PUBLIC LINKS
// ========================================

function renderPublicLinks(
    links
) {

    const featuredSection =
        document.getElementById(
            "publicFeaturedSection"
        );

    const linksSection =
        document.getElementById(
            "publicLinksSection"
        );


    if (
        !featuredSection ||
        !linksSection
    ) {

        return;

    }


    const featuredLink =
        links.find(
            link =>
                Number(link.featured) === 1
        );


    const normalLinks =
        links.filter(
            link =>
                Number(link.featured) !== 1
        );


    // ----------------------------------------
    // FEATURED
    // ----------------------------------------

    if (featuredLink) {

        featuredSection.hidden = false;

        featuredSection.innerHTML = `

            <div class="section-label">
                <span>
                    FEATURED PROJECT
                </span>
            </div>


            <div class="project-card">

                <div class="project-icon">
                    ${escapeHtml(
                        getPublicLinkIcon(
                            featuredLink.url
                        )
                    )}
                </div>


                <div class="project-info">

                    <h2>
                        ${escapeHtml(
                            featuredLink.name
                        )}
                    </h2>


                    <p>
                        ${escapeHtml(
                            featuredLink.description ||
                            "Featured project and link."
                        )}
                    </p>


                    <a
                        class="project-button"
                        href="${escapeHtml(
                            featuredLink.url
                        )}"
                        target="_blank"
                        rel="noopener noreferrer"
                        data-track="${escapeHtml(
                            featuredLink.name
                        )}"
                    >
                        View Project →
                    </a>

                </div>

            </div>

        `;

    } else {

        featuredSection.hidden = true;

    }


    // ----------------------------------------
    // NORMAL LINKS
    // ----------------------------------------

    linksSection.innerHTML = `

        <div class="section-label">
            <span>
                FIND ME
            </span>
        </div>


        ${
            normalLinks.length
                ? normalLinks
                    .map(
                        link => `
                            <a
                                class="link-card"
                                href="${escapeHtml(
                                    link.url
                                )}"
                                target="_blank"
                                rel="noopener noreferrer"
                                data-track="${escapeHtml(
                                    link.name
                                )}"
                            >

                                <span
                                    class="link-icon"
                                >
                                    ${escapeHtml(
                                        getPublicLinkIcon(
                                            link.url
                                        )
                                    )}
                                </span>


                                <span
                                    class="link-name"
                                >
                                    ${escapeHtml(
                                        link.name
                                    )}
                                </span>


                                <span
                                    class="arrow"
                                >
                                    ↗
                                </span>

                            </a>
                        `
                    )
                    .join("")
                : `
                    <div
                        class="link-card"
                        style="justify-content:center;"
                    >
                        No links available.
                    </div>
                `
        }

    `;


    // Re-bind analytics after dynamic rendering.
    bindTrackedLinks();

}


// ========================================
// BIND CLICK TRACKING
// ========================================

function bindTrackedLinks() {

    const trackedLinks =
        document.querySelectorAll(
            "[data-track]"
        );


    console.log(
        `Tracking ${trackedLinks.length} links.`
    );


    trackedLinks.forEach(
        link => {

            // Prevent duplicate listeners.
            if (
                link.dataset.analyticsBound === "1"
            ) {

                return;

            }


            link.dataset.analyticsBound =
                "1";


            link.addEventListener(
                "click",
                () => {

                    const linkName =
                        link.dataset.track;


                    console.log(
                        `📊 Tracking click: ${linkName}`
                    );


                    saveLocalClick(
                        linkName
                    );


                    sendEventToBackend(
                        "click",
                        linkName
                    );

                }
            );

        }
    );

}

// ========================================
// SEND EVENT TO PYTHON BACKEND
// ========================================

async function sendEventToBackend(
    eventType,
    linkName
) {

    try {

        const response =
            await fetch(
                ANALYTICS_API,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        event_type:
                            eventType,

                        link_name:
                            linkName,

                        timezone:
                            Intl.DateTimeFormat()
                                .resolvedOptions()
                                .timeZone || null
                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                `Server returned ${response.status}`
            );

        }


        const result =
            await response.json();


        if (result.success) {

            console.log(
                `✅ ${linkName} saved to database`
            );

        }

    } catch (error) {

        console.warn(
            "⚠️ Could not reach analytics backend:",
            error.message
        );

    }

}


// ========================================
// LOCAL CLICK STORAGE
// ========================================

function saveLocalClick(linkName) {

    const key =
        "manas_linkhub_analytics";


    let analyticsData =
        loadAnalytics();


    if (!analyticsData.links[linkName]) {

        analyticsData.links[linkName] = 0;

    }


    analyticsData.links[linkName]++;


    analyticsData.totalClicks++;


    analyticsData.lastClick =
        new Date().toISOString();


    localStorage.setItem(
        key,
        JSON.stringify(
            analyticsData
        )
    );


    console.log(
        `Local ${linkName} clicks:`,
        analyticsData.links[linkName]
    );

}


// ========================================
// LOAD LOCAL ANALYTICS
// ========================================

function loadAnalytics() {

    const key =
        "manas_linkhub_analytics";


    const savedData =
        localStorage.getItem(key);


    if (!savedData) {

        return {

            totalClicks: 0,

            links: {},

            lastClick: null

        };

    }


    try {

        return JSON.parse(
            savedData
        );

    } catch (error) {

        console.error(
            "Could not read local analytics:",
            error
        );


        return {

            totalClicks: 0,

            links: {},

            lastClick: null

        };

    }

}


// ========================================
// SHOW LOCAL ANALYTICS
// ========================================

function showAnalytics() {

    const analyticsData =
        loadAnalytics();


    console.table(
        analyticsData.links
    );


    console.log(
        "Total clicks:",
        analyticsData.totalClicks
    );


    console.log(
        "Last click:",
        analyticsData.lastClick
    );

}


// ========================================
// RESET LOCAL ANALYTICS
// ========================================

function resetAnalytics() {

    localStorage.removeItem(
        "manas_linkhub_analytics"
    );


    console.log(
        "🗑️ Local analytics reset."
    );

}
