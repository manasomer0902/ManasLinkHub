// ========================================
// MANAS LINK HUB — ANALYTICS
// V2.0
// Local + Python Backend Tracking
// ========================================

const ANALYTICS_API =
    "https://manaslinkhub.onrender.com/api/event";

document.addEventListener("DOMContentLoaded", () => {

    console.log(
        "Manas Link Hub Analytics loaded."
    );


    const trackedLinks =
        document.querySelectorAll("[data-track]");


    console.log(
        `Tracking ${trackedLinks.length} links.`
    );


    trackedLinks.forEach((link) => {

        link.addEventListener("click", () => {

            const linkName =
                link.dataset.track;


            console.log(
                `📊 Tracking click: ${linkName}`
            );


            // Save locally
            saveLocalClick(linkName);


            // Send to Python backend
            sendEventToBackend(
                "click",
                linkName
            );

        });

    });

});


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
                            linkName

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
