
// ========================================
// CONFIGURATION
// ========================================

const API_URL =
    window.location.origin;

// ========================================
// GET SELECTED TIME RANGE
// ========================================

function getTimeRange() {

    const range =
        document.getElementById(
            "timeRange"
        ).value;

    const now =
        new Date();

    let start = null;
    let end = null;

    // ----------------------------------------
    // TODAY
    // ----------------------------------------

    if (range === "today") {

        start =
            new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate()
            );

        end =
            new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate() + 1
            );
    }


    // ========================================
    // YESTERDAY
    // ========================================

    else if (range === "yesterday") {

        start =
            new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate() - 1
            );

        end =
            new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate()
            );
    }

    // ----------------------------------------
    // LAST 7 DAYS
    // ----------------------------------------

    else if (range === "7days") {

        end = now;

        start =
            new Date(
                now.getTime()
                -
                7 * 24 * 60 * 60 * 1000
            );
    }

    // ----------------------------------------
    // LAST 30 DAYS
    // ----------------------------------------

    else if (range === "30days") {

        end = now;

        start =
            new Date(
                now.getTime()
                -
                30 * 24 * 60 * 60 * 1000
            );
    }

    // ----------------------------------------
    // ALL TIME
    // ----------------------------------------

    else {

        return {
            start: null,
            end: null
        };
    }

    return {
        start: start.toISOString(),
        end: end.toISOString()
    };
}


// ========================================
// LOAD SUMMARY
// ========================================

async function loadSummary() {

    const range =
        getTimeRange();

    const params =
        new URLSearchParams();

    if (range.start && range.end) {

        params.set(
            "start",
            range.start
        );

        params.set(
            "end",
            range.end
        );
    }

    const query =
        params.toString();

    const response =
        await fetch(
            `${API_URL}/api/analytics${
                query
                    ? "?" + query
                    : ""
            }`
        );

    if (response.status === 401) {

        window.location.href =
            "/admin/login";

        return null;
    }

    if (!response.ok) {

        throw new Error(
            "Analytics API failed"
        );
    }

    return await response.json();
}

// ========================================
// LOAD RECENT ACTIVITY
// ========================================

async function loadRecentActivity() {

    const range =
        getTimeRange();

    const params =
        new URLSearchParams();

    if (range.start && range.end) {

        params.set(
            "start",
            range.start
        );

        params.set(
            "end",
            range.end
        );
    }

    const query =
        params.toString();

    const response =
        await fetch(
            `${API_URL}/api/recent${
                query
                    ? "?" + query
                    : ""
            }`
        );

    if (response.status === 401) {

        window.location.href =
            "/admin/login";

        return null;
    }

    if (!response.ok) {

        throw new Error(
            "Recent activity API failed"
        );
    }

    return await response.json();
}

// ========================================
// COMPARISON HELPERS
// ========================================

function getDateRange(
    start,
    end
) {

    return {
        start: start.toISOString(),
        end: end.toISOString()
    };

}


// ========================================
// FETCH SUMMARY FOR RANGE
// ========================================

async function fetchComparisonSummary(
    start,
    end
) {

    const range =
        getDateRange(
            start,
            end
        );

    const params =
        new URLSearchParams();

    params.set(
        "start",
        range.start
    );

    params.set(
        "end",
        range.end
    );

    const response =
        await fetch(
            `${API_URL}/api/analytics?${params.toString()}`
        );

    if (response.status === 401) {

        window.location.href =
            "/admin/login";

        return null;
    }

    if (!response.ok) {

        throw new Error(
            "Comparison analytics API failed"
        );
    }

    return await response.json();

}


// ========================================
// PERCENTAGE CHANGE
// ========================================

function calculateChange(
    current,
    previous
) {

    if (previous === 0) {

        if (current === 0) {
            return "—";
        }

        return "New";

    }

    const change =
        (
            (current - previous) /
            previous
        ) * 100;

    const sign =
        change > 0
            ? "+"
            : "";

    return `${sign}${change.toFixed(1)}%`;

}


// ========================================
// RENDER COMPARISON
// ========================================

function renderComparisonCard(
    elementId,
    current,
    previous
) {

    const container =
        document.getElementById(
            elementId
        );

    const visitsChange =
        calculateChange(
            current.visits,
            previous.visits
        );

    const clicksChange =
        calculateChange(
            current.clicks,
            previous.clicks
        );

    container.innerHTML = `

        <div class="comparison-row">

            <span class="comparison-label">
                Visits
            </span>

            <span class="comparison-number">
                ${current.visits}

                <span class="comparison-change">
                    ${visitsChange}
                </span>
            </span>

        </div>


        <div class="comparison-row">

            <span class="comparison-label">
                Clicks
            </span>

            <span class="comparison-number">
                ${current.clicks}

                <span class="comparison-change">
                    ${clicksChange}
                </span>
            </span>

        </div>

    `;

}


// ========================================
// LOAD COMPARISONS
// ========================================

async function loadComparisons() {

    const now =
        new Date();


    // ========================================
    // TODAY VS YESTERDAY
    // ========================================

    const todayStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate()
        );

    const tomorrowStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate() + 1
        );

    const yesterdayStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate() - 1
        );


    // ========================================
    // THIS WEEK VS PREVIOUS WEEK
    // Monday = start of week
    // ========================================

    const day =
        now.getDay();

    const daysFromMonday =
        day === 0
            ? 6
            : day - 1;

    const currentWeekStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate()
                -
                daysFromMonday
        );

    const previousWeekStart =
        new Date(
            currentWeekStart.getFullYear(),
            currentWeekStart.getMonth(),
            currentWeekStart.getDate() - 7
        );


    // ========================================
    // THIS MONTH VS PREVIOUS MONTH
    // ========================================

    const currentMonthStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            1
        );

    const previousMonthStart =
        new Date(
            now.getFullYear(),
            now.getMonth() - 1,
            1
        );


    const previousMonthEnd =
        new Date(
            currentMonthStart
        );


    // ========================================
    // FETCH ALL COMPARISONS
    // ========================================

    const [

        todayData,
        yesterdayData,

        thisWeekData,
        previousWeekData,

        thisMonthData,
        previousMonthData

    ] = await Promise.all([

        fetchComparisonSummary(
            todayStart,
            tomorrowStart
        ),

        fetchComparisonSummary(
            yesterdayStart,
            todayStart
        ),

        fetchComparisonSummary(
            currentWeekStart,
            now
        ),

        fetchComparisonSummary(
            previousWeekStart,
            currentWeekStart
        ),

        fetchComparisonSummary(
            currentMonthStart,
            now
        ),

        fetchComparisonSummary(
            previousMonthStart,
            previousMonthEnd
        )

    ]);


    // ========================================
    // CONVERT EVENTS TO VISITS / CLICKS
    // ========================================

    function extractCounts(
        data
    ) {

        if (!data) {

            return {
                visits: 0,
                clicks: 0
            };

        }

        const events =
            data.total_events || 0;

        const clicks =
            data.total_clicks || 0;

        return {
            visits:
                events - clicks,
            clicks:
                clicks
        };

    }


    const today =
        extractCounts(
            todayData
        );

    const yesterday =
        extractCounts(
            yesterdayData
        );

    const thisWeek =
        extractCounts(
            thisWeekData
        );

    const previousWeek =
        extractCounts(
            previousWeekData
        );

    const thisMonth =
        extractCounts(
            thisMonthData
        );

    const previousMonth =
        extractCounts(
            previousMonthData
        );


    // ========================================
    // RENDER
    // ========================================

    renderComparisonCard(
        "todayComparison",
        today,
        yesterday
    );

    renderComparisonCard(
        "weekComparison",
        thisWeek,
        previousWeek
    );

    renderComparisonCard(
        "monthComparison",
        thisMonth,
        previousMonth
    );

}
// ========================================
// LOAD EVERYTHING
// ========================================

async function loadDashboard() {

    setLoadingState(true);

    try {

        const [
            summary,
            recent,
            chartData
        ] = await Promise.all([

            loadSummary(),

            loadRecentActivity(),

            loadChartData()

        ]);

        if (
            !summary ||
            !recent ||
            !chartData
        ) {

            return;
        }

        updateSummary(
            summary
        );

        updateVisitorInsights(
            summary
        );

        renderLinks(
            summary.link_clicks
        );

        renderRecentActivity(
            recent.events
        );

        checkForNewActivity(
            recent.events
        );


        renderCharts(
            chartData.events,
            summary.visitor_insights || {}

        );

        await loadComparisons();

        updateLastUpdated();

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

        showError();

    } finally {

        setLoadingState(false);

    }
}
// ========================================
// UPDATE SUMMARY
// ========================================

function updateSummary(
    data
) {

    document.getElementById(
        "totalEvents"
    ).textContent =
        data.total_events;


    document.getElementById(
        "totalClicks"
    ).textContent =
        data.total_clicks;


    document.getElementById(
        "linksTracked"
    ).textContent =
        data.link_clicks.length;


    // ========================================
    // TOP LINK
    // ========================================

    const topLink =
        data.link_clicks.length
            ? data.link_clicks[0]
            : null;


    if (topLink) {

        const totalClicks =
            data.total_clicks;


        const share =
            totalClicks > 0
                ? (
                    topLink.clicks /
                    totalClicks
                ) * 100
                : 0;


        document.getElementById(
            "topLink"
        ).textContent =
            formatLinkName(
                topLink.link_name
            );


        document.getElementById(
            "topLinkClicks"
        ).textContent =
            `${topLink.clicks} ${
                topLink.clicks === 1
                    ? "click"
                    : "clicks"
            } · ${share.toFixed(1)}%`;

    } else {

        document.getElementById(
            "topLink"
        ).textContent =
            "No clicks";


        document.getElementById(
            "topLinkClicks"
        ).textContent =
            "—";

    }

}

// ========================================
// UPDATE VISITOR INSIGHTS
// ========================================

function updateVisitorInsights(
    data
) {

    const insights =
        data.visitor_insights || {};


    document.getElementById(
        "uniqueVisitors"
    ).textContent =
        insights.unique_visitors ?? 0;


    document.getElementById(
        "repeatVisitors"
    ).textContent =
        insights.repeat_visitors ?? 0;


    // ----------------------------------------
    // TOP BROWSER
    // ----------------------------------------

    const browsers =
        insights.browser_breakdown || [];

    document.getElementById(
        "topBrowser"
    ).textContent =
        browsers.length
            ? browsers[0].name
            : "None";


    // ----------------------------------------
    // TOP DEVICE
    // ----------------------------------------

    const devices =
        insights.device_breakdown || [];

    document.getElementById(
        "topDevice"
    ).textContent =
        devices.length
            ? devices[0].name
            : "None";


    // ----------------------------------------
    // TOP OPERATING SYSTEM
    // ----------------------------------------

    const operatingSystems =
        insights.os_breakdown || [];

    document.getElementById(
        "topOperatingSystem"
    ).textContent =
        operatingSystems.length
            ? operatingSystems[0].name
            : "None";


    renderBreakdown(
        "browserBreakdown",
        browsers
    );


    renderBreakdown(
        "deviceBreakdown",
        devices
    );


    renderBreakdown(
        "osBreakdown",
        operatingSystems
    );


    renderBreakdown(
        "referrerBreakdown",
        insights.referrer_breakdown || []
    );


    renderLocationBreakdown(
        insights.location_breakdown || []
    );
}

// ========================================
// RENDER INSIGHT BREAKDOWN
// ========================================

function renderBreakdown(
    elementId,
    items
) {

    const container =
        document.getElementById(
            elementId
        );

    if (!items.length) {

        container.innerHTML = `
            <div class="empty">
                No data available.
            </div>
        `;

        return;
    }

    container.innerHTML =
        items
            .slice(0, 5)
            .map(
                item => `
                    <div class="breakdown-row">

                        <span
                            class="breakdown-name"
                            title="${escapeHtml(
                                item.name
                            )}"
                        >
                            ${escapeHtml(
                                item.name
                            )}
                        </span>

                        <span
                            class="breakdown-count"
                        >
                            ${item.count}
                        </span>

                    </div>
                `
            )
            .join("");
}

// ========================================
// RENDER LOCATION BREAKDOWN
// ========================================

function renderLocationBreakdown(
    items
) {

    const container =
        document.getElementById(
            "locationBreakdown"
        );

    if (!items.length) {

        container.innerHTML = `
            <div class="empty">
                No location data available yet.
            </div>
        `;

        return;
    }

    container.innerHTML =
        items
            .slice(0, 8)
            .map(
                item => `

                    <div class="breakdown-row">

                        <span
                            class="breakdown-name"
                        >
                            ${escapeHtml(
                                item.name
                            )}
                        </span>

                        <span
                            class="breakdown-count"
                        >
                            ${item.count}
                        </span>

                    </div>

                `
            )
            .join("");
}

// ========================================
// RESET LINK ANALYTICS
// ========================================

function resetLinkAnalytics() {

selectedLinkAnalytics = null;


document.getElementById(
"linkTodayClicks"
).textContent = "0";


document.getElementById(
"linkWeekClicks"
).textContent = "0";


document.getElementById(
"linkMonthClicks"
).textContent = "0";


document.getElementById(
"linkAllTimeClicks"
).textContent = "0";


document.getElementById(
"linkPeakHour"
).textContent =
"No peak activity yet";


document.getElementById(
"linkPeakDay"
).textContent =
"No click history yet";


document.getElementById(
"linkTrafficSources"
).innerHTML = `
<div class="empty">
    No traffic source data yet.
</div>
`;


document.getElementById(
"linkRecentClicks"
).innerHTML = `
<div class="empty">
    No clicks recorded yet.
</div>
`;


if (linkHistoryChart) {

linkHistoryChart.destroy();

linkHistoryChart = null;

}

}

// ========================================
// RENDER LINK PERFORMANCE
// ========================================

function renderLinks(
links
) {

const container =
document.getElementById(
    "linkList"
);


const select =
document.getElementById(
    "linkAnalyticsSelect"
);


if (!links.length) {

container.innerHTML = `
    <div class="empty">
        No clicks recorded yet.
    </div>
`;


select.innerHTML = `
    <option value="">
        No links available
    </option>
`;


select.disabled = true;

resetLinkAnalytics();

return;
}


select.disabled = false;


// ========================================
// HIGHEST CLICK COUNT
// ========================================

const highest =
Math.max(
    ...links.map(
        item =>
            item.clicks
    )
);


// ========================================
// TOTAL CLICKS
// ========================================

const totalClicks =
links.reduce(
    (total, item) =>
        total + item.clicks,
    0
);


// ========================================
// LINK PERFORMANCE
// ========================================

container.innerHTML =
links.map(
    item => {

        const barPercentage =
            highest > 0
                ? (
                    item.clicks /
                    highest
                ) * 100
                : 0;


        const sharePercentage =
            totalClicks > 0
                ? (
                    item.clicks /
                    totalClicks
                ) * 100
                : 0;


        return `
            <div
                class="link-row"
                data-link-name="${escapeHtml(
                    item.link_name
                )}"
                style="cursor: pointer;"
                title="View link analytics"
            >

                <div class="link-top">

                    <span
                        class="link-name"
                    >
                        ${escapeHtml(
                            formatLinkName(
                                item.link_name
                            )
                        )}
                    </span>


                    <span
                        class="link-count"
                    >
                        ${item.clicks}

                        ${
                            item.clicks === 1
                                ? "click"
                                : "clicks"
                        }

                        · ${sharePercentage.toFixed(1)}%
                    </span>

                </div>


                <div class="bar">

                    <div
                        class="bar-fill"
                        style="
                            width:
                            ${barPercentage}%;
                        "
                    ></div>

                </div>

            </div>
        `;
    }
).join("");


// ========================================
// LINK SELECT OPTIONS
// ========================================

select.innerHTML =
links.map(
    item => `
        <option
            value="${escapeHtml(
                item.link_name
            )}"
        >
            ${escapeHtml(
                formatLinkName(
                    item.link_name
                )
            )}
        </option>
    `
).join("");


const availableLinks =
links.map(
    item =>
        item.link_name
);


if (
!selectedLinkAnalytics ||
!availableLinks.includes(
    selectedLinkAnalytics
)
) {

selectedLinkAnalytics =
    availableLinks[0];

}


select.value =
selectedLinkAnalytics;


select.onchange =
function () {

    selectedLinkAnalytics =
        this.value;

    loadLinkAnalytics(
        selectedLinkAnalytics
    );

};


// ========================================
// CLICKABLE LINK PERFORMANCE ROWS
// ========================================

container
.querySelectorAll(
    ".link-row[data-link-name]"
)
.forEach(
    row => {

        row.addEventListener(
            "click",
            function () {

                selectedLinkAnalytics =
                    this.dataset.linkName;


                select.value =
                    selectedLinkAnalytics;


                loadLinkAnalytics(
                    selectedLinkAnalytics
                );


                document
                    .getElementById(
                        "linkAnalyticsSelect"
                    )
                    .scrollIntoView(
                        {
                            behavior:
                                "smooth",
                            block:
                                "center"
                        }
                    );

            }
        );

    }
);


// ========================================
// LOAD CURRENT LINK
// ========================================

loadLinkAnalytics(
selectedLinkAnalytics
);

}

// ========================================
// PHASE 5 — LINK ANALYTICS RANGES
// ========================================

function getLinkAnalyticsRanges() {

    const now =
        new Date();


    // ========================================
    // TODAY
    // ========================================

    const todayStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate()
        );


    const tomorrowStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate() + 1
        );


    // ========================================
    // THIS WEEK
    // Monday = first day
    // ========================================

    const day =
        now.getDay();


    const daysFromMonday =
        day === 0
            ? 6
            : day - 1;


    const weekStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate()
                - daysFromMonday
        );


    // ========================================
    // THIS MONTH
    // ========================================

    const monthStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            1
        );


    // ========================================
    // HISTORY — LAST 30 DAYS
    // ========================================

    const historyStart =
        new Date(
            now.getFullYear(),
            now.getMonth(),
            now.getDate() - 29
        );


    return {

        todayStart:
            todayStart.toISOString(),

        todayEnd:
            tomorrowStart.toISOString(),

        weekStart:
            weekStart.toISOString(),

        weekEnd:
            now.toISOString(),

        monthStart:
            monthStart.toISOString(),

        monthEnd:
            now.toISOString(),

        historyStart:
            historyStart.toISOString(),

        historyEnd:
            tomorrowStart.toISOString()

    };

}


// ========================================
// LOAD INDIVIDUAL LINK ANALYTICS
// ========================================

async function loadLinkAnalytics(
    linkName
) {

    if (!linkName) {
        return;
    }


    const ranges =
        getLinkAnalyticsRanges();


    const params =
        new URLSearchParams();


    params.set(
        "link_name",
        linkName
    );


    params.set(
        "today_start",
        ranges.todayStart
    );


    params.set(
        "today_end",
        ranges.todayEnd
    );


    params.set(
        "week_start",
        ranges.weekStart
    );


    params.set(
        "week_end",
        ranges.weekEnd
    );


    params.set(
        "month_start",
        ranges.monthStart
    );


    params.set(
        "month_end",
        ranges.monthEnd
    );


    params.set(
        "history_start",
        ranges.historyStart
    );


    params.set(
        "history_end",
        ranges.historyEnd
    );


    params.set(
        "timezone_offset",
        new Date().getTimezoneOffset()
    );


    try {

        const response =
            await fetch(
                `${API_URL}/api/link-analytics?${params.toString()}`
            );


        if (
            response.status === 401
        ) {

            window.location.href =
                "/admin/login";

            return;

        }


        if (!response.ok) {

            throw new Error(
                "Link analytics API failed"
            );

        }


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.message ||
                "Link analytics failed"
            );

        }


        renderLinkAnalytics(
            data
        );

    } catch (error) {

        console.error(
            "Link analytics error:",
            error
        );


        document.getElementById(
            "linkTrafficSources"
        ).innerHTML = `
            <div class="empty error">
                Unable to load link analytics.
            </div>
        `;

        document.getElementById(
            "linkRecentClicks"
        ).innerHTML = `
            <div class="empty error">
                Unable to load click details.
            </div>
        `;

    }

}


// ========================================
// RENDER LINK ANALYTICS
// ========================================

function renderLinkAnalytics(
    data
) {

    const periods =
        data.periods || {};


    document.getElementById(
        "linkTodayClicks"
    ).textContent =
        periods.today ?? 0;


    document.getElementById(
        "linkWeekClicks"
    ).textContent =
        periods.week ?? 0;


    document.getElementById(
        "linkMonthClicks"
    ).textContent =
        periods.month ?? 0;


    document.getElementById(
        "linkAllTimeClicks"
    ).textContent =
        periods.all_time ?? 0;


    // ========================================
    // PEAK ACTIVITY
    // ========================================

    const peak =
        data.peak_activity || {};


    const peakHour =
        peak.hour;


    const peakDay =
        peak.day;


    document.getElementById(
        "linkPeakHour"
    ).textContent =
        peakHour
            ? `${peakHour.label} · ${peakHour.clicks} ${
                peakHour.clicks === 1
                    ? "click"
                    : "clicks"
            }`
            : "No peak activity yet";


    document.getElementById(
        "linkPeakDay"
    ).textContent =
        peakDay
            ? `${peakDay.label} is the busiest day · ${peakDay.clicks} ${
                peakDay.clicks === 1
                    ? "click"
                    : "clicks"
            }`
            : "No click history yet";


    // ========================================
    // TRAFFIC SOURCES
    // ========================================

    const sources =
        data.traffic_sources || [];


    const sourceContainer =
        document.getElementById(
            "linkTrafficSources"
        );


    if (!sources.length) {

        sourceContainer.innerHTML = `
            <div class="empty">
                No traffic source data yet.
            </div>
        `;

    } else {

        sourceContainer.innerHTML =
            sources
                .slice(0, 8)
                .map(
                    source => `
                        <div
                            class="link-analytics-row"
                        >

                            <span
                                class="link-analytics-name"
                            >
                                ${escapeHtml(
                                    source.name
                                )}
                            </span>

                            <span
                                class="link-analytics-count"
                            >
                                ${source.count}
                            </span>

                        </div>
                    `
                )
                .join("");

    }


    // ========================================
    // RECENT CLICK DETAILS
    // ========================================

    const recentClicks =
        data.recent_clicks || [];


    const recentContainer =
        document.getElementById(
            "linkRecentClicks"
        );


    if (!recentClicks.length) {

        recentContainer.innerHTML = `
            <div class="empty">
                No clicks recorded yet.
            </div>
        `;

    } else {

        recentContainer.innerHTML =
            recentClicks
                .map(
                    click => {

                        const referrer =
                            click.referrer ||
                            "Direct";


                        const source =
                            click.traffic_source ||
                            "Direct";


                        return `
                            <div
                                class="link-click-row"
                            >

                                <div
                                    class="link-click-time"
                                >
                                    ${escapeHtml(
                                        formatDate(
                                            click.timestamp
                                        )
                                    )}
                                </div>


                                <div
                                    class="link-click-meta"
                                >

                                    <span>
                                        ${escapeHtml(
                                            click.browser
                                        )}
                                    </span>

                                    <span>
                                        ${escapeHtml(
                                            click.device
                                        )}
                                    </span>

                                    <span>
                                        ${escapeHtml(
                                            source
                                        )}
                                    </span>

                                    <span>
                                        ${escapeHtml(
                                            referrer
                                        )}
                                    </span>

                                </div>

                            </div>
                        `;

                    }
                )
                .join("");

    }


    // ========================================
    // PERFORMANCE HISTORY
    // ========================================

    renderLinkHistory(
        data.history || []
    );

}


// ========================================
// RENDER LINK HISTORY
// ========================================

function renderLinkHistory(
    history
) {

    if (linkHistoryChart) {

        linkHistoryChart.destroy();

    }


    const historyMap = {};


    history.forEach(
        item => {

            historyMap[item.date] =
                item.clicks;

        }
    );


    const start =
        new Date();


    start.setHours(
        0,
        0,
        0,
        0
    );


    start.setDate(
        start.getDate() - 29
    );


    const labels = [];

    const values = [];


    for (
        let index = 0;
        index < 30;
        index++
    ) {

        const date =
            new Date(
                start
            );


        date.setDate(
            start.getDate() +
            index
        );


        const key =
            `${date.getFullYear()}-${
                String(
                    date.getMonth() + 1
                ).padStart(
                    2,
                    "0"
                )
            }-${
                String(
                    date.getDate()
                ).padStart(
                    2,
                    "0"
                )
            }`;


        labels.push(
            date.toLocaleDateString(
                undefined,
                {
                    month:
                        "short",
                    day:
                        "numeric"
                }
            )
        );


        values.push(
            historyMap[key] || 0
        );

    }


    linkHistoryChart =
        new Chart(
            document.getElementById(
                "linkHistoryChart"
            ),
            {

                type: "line",

                data: {

                    labels:
                        labels,

                    datasets: [{

                        label:
                            "Clicks",

                        data:
                            values,

                        tension:
                            0.35,

                        borderWidth:
                            2,

                        fill:
                            false

                    }]

                },

                options: {

                    responsive:
                        true,

                    maintainAspectRatio:
                        false,

                    plugins: {

                        legend: {

                            display:
                                false

                        }

                    },

                    scales: {

                        x: {

                            ticks: {

                                color:
                                    "#9698a2",

                                maxTicksLimit:
                                    10

                            },

                            grid: {

                                color:
                                    "rgba(255,255,255,0.05)"

                            }

                        },

                        y: {

                            beginAtZero:
                                true,

                            ticks: {

                                color:
                                    "#9698a2",

                                precision:
                                    0

                            },

                            grid: {

                                color:
                                    "rgba(255,255,255,0.05)"

                            }

                        }

                    }

                }

            }
        );

}
        // ========================================
// RENDER RECENT ACTIVITY
// ========================================

function renderRecentActivity(
    events
) {

    const container =
        document.getElementById(
            "activityList"
        );

    if (!events.length) {

        container.innerHTML = `
            <div class="empty">
                No activity recorded yet.
            </div>
        `;

        return;
    }

    container.innerHTML =
        events.map(
            event => {

                const date =
                    formatDate(
                        event.timestamp
                    );

                const referrer =
                    event.referrer
                        ? formatReferrer(
                            event.referrer
                        )
                        : "Direct";

                const browser =
                    detectBrowser(
                        event.user_agent
                    );

                const device =
                    detectDevice(
                        event.user_agent
                    );

                const ip =
                    event.ip_address ||
                    "Unknown";

                return `
                    <div class="activity">

                        <div class="activity-left">

                            <div
                                class="activity-name"
                            >
                                ${escapeHtml(
                                    formatLinkName(
                                        event.link_name
                                    )
                                )}
                            </div>

                            <div
                                class="activity-meta"
                            >

                                <span
                                    class="activity-badge"
                                >
                                    ${escapeHtml(
                                        event.event_type
                                    )}
                                </span>

                                <span>
                                    ${escapeHtml(
                                        browser
                                    )}
                                </span>

                                <span>
                                    ${escapeHtml(
                                        device
                                    )}
                                </span>

                                <span>
                                    ${escapeHtml(
                                        referrer
                                    )}
                                </span>

                                <span>
                                    ${escapeHtml(
                                        ip
                                    )}
                                </span>

                            </div>

                        </div>

                        <div
                            class="activity-time"
                        >
                            ${escapeHtml(
                                date
                            )}
                        </div>

                    </div>
                `;

            }
        ).join("");
}

// ========================================
// DETECT BROWSER
// ========================================

function detectBrowser(
userAgent
) {

if (!userAgent) {
    return "Unknown";
}

const ua =
    userAgent.toLowerCase();

if (ua.includes("edg/")) {
    return "Edge";
}

if (
    ua.includes("opr/") ||
    ua.includes("opera")
) {
    return "Opera";
}

if (ua.includes("firefox/")) {
    return "Firefox";
}

if (
    ua.includes("chrome/") &&
    !ua.includes("edg/")
) {
    return "Chrome";
}

if (
    ua.includes("safari/") &&
    !ua.includes("chrome/")
) {
    return "Safari";
}

return "Other";
}


// ========================================
// DETECT DEVICE
// ========================================

function detectDevice(
userAgent
) {

if (!userAgent) {
    return "Unknown";
}

const ua =
    userAgent.toLowerCase();

if (
    ua.includes("ipad") ||
    ua.includes("tablet")
) {
    return "Tablet";
}

if (
    ua.includes("mobile") ||
    ua.includes("iphone") ||
    ua.includes("android")
) {
    return "Mobile";
}

return "Desktop";
}

// ========================================
// DETECT OPERATING SYSTEM
// ========================================

function detectOperatingSystem(
    userAgent
) {

    if (!userAgent) {
        return "Unknown";
    }

    const ua =
        userAgent.toLowerCase();

    if (
        ua.includes("iphone") ||
        ua.includes("ipad") ||
        ua.includes("ipod")
    ) {
        return "iOS";
    }

    if (
        ua.includes("android")
    ) {
        return "Android";
    }

    if (
        ua.includes("windows phone")
    ) {
        return "Windows Phone";
    }

    if (
        ua.includes("windows")
    ) {
        return "Windows";
    }

    if (
        ua.includes("macintosh") ||
        ua.includes("mac os x")
    ) {
        return "macOS";
    }

    if (
        ua.includes("cros")
    ) {
        return "ChromeOS";
    }

    if (
        ua.includes("linux")
    ) {
        return "Linux";
    }

    return "Other";
}


// ========================================
// DETECT TRAFFIC SOURCE
// ========================================

function detectTrafficSource(
    referrer
) {

    if (!referrer) {
        return "Direct";
    }

    try {

        const hostname =
            new URL(
                referrer
            ).hostname.toLowerCase();

        if (
            hostname.includes(
                "instagram.com"
            )
        ) {
            return "Instagram";
        }

        if (
            hostname.includes(
                "facebook.com"
            )
        ) {
            return "Facebook";
        }

        if (
            hostname.includes(
                "linkedin.com"
            )
        ) {
            return "LinkedIn";
        }

        if (
            hostname.includes(
                "github.com"
            )
        ) {
            return "GitHub";
        }

        if (
            hostname.includes(
                "youtube.com"
            )
        ) {
            return "YouTube";
        }

        if (
            hostname.includes(
                "google."
            )
        ) {
            return "Google";
        }

        if (
            hostname.includes(
                "bing.com"
            )
        ) {
            return "Bing";
        }

        return hostname;

    } catch {

        return "Other";

    }

}
// ========================================
// ESCAPE HTML
// ========================================

function escapeHtml(
value
) {

return String(value ?? "")
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
// FORMAT LINK NAME
// ========================================

function formatLinkName(
    name
) {

    if (!name) {

        return "Unknown";

    }

    return name
        .charAt(0)
        .toUpperCase()
        + name.slice(1);

}

// ========================================
// FORMAT REFERRER
// ========================================

function formatReferrer(
    referrer
) {

    try {

        const url =
            new URL(referrer);

        return url.hostname;

    } catch {

        return referrer;

    }

}

// ========================================
// FORMAT DATE
// ========================================

function formatDate(
    timestamp
) {

    if (!timestamp) {

        return "Unknown";

    }

    const date =
        new Date(timestamp);

    return date.toLocaleString(
        undefined,
        {
            dateStyle: "medium",
            timeStyle: "short"
        }
    );

}

// ========================================
// LAST UPDATED
// ========================================

function updateLastUpdated() {

    const now =
        new Date();

    document.getElementById(
        "lastUpdated"
    ).textContent =
        `Last updated: ${
            now.toLocaleTimeString()
        }`;

}

// ========================================
// ERROR STATE
// ========================================

function showError() {

    document.getElementById(
        "linkList"
    ).innerHTML = `

        <div class="empty error">

            Unable to connect to
            analytics server.

            <br><br>

            Make sure Flask is running.

        </div>

    `;

    document.getElementById(
        "activityList"
    ).innerHTML = `

        <div class="empty error">

            Unable to load recent activity.

        </div>

    `;

}

// ========================================
// CLEAR ANALYTICS
// ========================================

document.getElementById(
    "clearAnalyticsButton"
).addEventListener(
    "click",
    async function () {

        const confirmed =
            window.confirm(
                "Are you sure you want to clear ALL analytics data?\n\nThis cannot be undone."
            );

        if (!confirmed) {
            return;
        }

        const button =
            document.getElementById(
                "clearAnalyticsButton"
            );

        button.disabled = true;

        button.textContent =
            "Clearing...";

        try {

            const response =
                await fetch(
                    `${API_URL}/api/analytics/clear`,
                    {
                        method: "POST"
                    }
                );

            if (
                response.status === 401
            ) {

                window.location.href =
                    "/admin/login";

                return;
            }

            if (!response.ok) {

                throw new Error(
                    "Clear analytics failed"
                );
            }

            await response.json();

            await loadDashboard();

        } catch (error) {

            console.error(
                "Clear analytics error:",
                error
            );

            alert(
                "Unable to clear analytics."
            );

        } finally {

            button.disabled = false;

            button.textContent =
                "Clear Analytics";
        }
    }
);
// ========================================
// TIME RANGE CHANGE
// ========================================

document.getElementById(
    "timeRange"
).addEventListener(
    "change",
    loadDashboard
);

// ========================================
// LOAD CHART DATA
// ========================================

async function loadChartData() {

    const range =
        getTimeRange();

    const params =
        new URLSearchParams();

    if (range.start && range.end) {

        params.set(
            "start",
            range.start
        );

        params.set(
            "end",
            range.end
        );

    }

    const query =
        params.toString();

    const response =
        await fetch(
            `${API_URL}/api/chart-data${
                query
                    ? "?" + query
                    : ""
            }`
        );

    if (response.status === 401) {

        window.location.href =
            "/admin/login";

        return null;

    }

    if (!response.ok) {

        throw new Error(
            "Chart data API failed"
        );

    }

    return await response.json();

}

// ========================================
// RENDER ANALYTICS CHARTS
// ========================================

let visitsChart = null;
let clicksChart = null;
let linkClicksChart = null;
let activityHourChart = null;
let browserChart = null;
let deviceChart = null;
let osChart = null;
let referrerChart = null;
let visitorTypeChart = null;
let trafficSourceChart = null;
let linkHistoryChart = null;
let selectedLinkAnalytics = "";


function renderCharts(
    events,
    visitorInsights = {}
) {

    // ========================================
    // DATA GROUPS
    // ========================================

    const visitsByDate = {};
    const clicksByDate = {};
    const clicksByLink = {};

    const activityByHour =
        Array.from(
            { length: 24 },
            () => 0
        );

    const browserCounts = {};
    const deviceCounts = {};
    const osCounts = {};
    const referrerCounts = {};
    const trafficSourceCounts = {};

    const visitorTypeCounts = {};

    (
        visitorInsights.visitor_type_breakdown || []
    ).forEach(
        item => {

            visitorTypeCounts[item.name] =
                item.count;

        }
    );


    // ========================================
    // PROCESS EVENTS
    // ========================================

    events.forEach(
        event => {

            if (!event.timestamp) {
                return;
            }

            const date =
                new Date(
                    event.timestamp
                );

            if (
                isNaN(
                    date.getTime()
                )
            ) {
                return;
            }


            // ----------------------------------------
            // DATE
            // ----------------------------------------

            const dateKey =
                date.toLocaleDateString(
                    undefined,
                    {
                        month: "short",
                        day: "numeric"
                    }
                );


            // ----------------------------------------
            // VISITS
            // ----------------------------------------

            if (
                event.event_type === "visit"
            ) {

                visitsByDate[dateKey] =
                    (
                        visitsByDate[dateKey]
                        || 0
                    ) + 1;

            }


            // ----------------------------------------
            // CLICKS
            // ----------------------------------------

            if (
                event.event_type === "click"
            ) {

                clicksByDate[dateKey] =
                    (
                        clicksByDate[dateKey]
                        || 0
                    ) + 1;


                const link =
                    formatLinkName(
                        event.link_name
                    );

                clicksByLink[link] =
                    (
                        clicksByLink[link]
                        || 0
                    ) + 1;

            }


            // ----------------------------------------
            // ACTIVITY BY HOUR
            // ----------------------------------------

            const hour =
                date.getHours();

            activityByHour[hour]++;


            // ----------------------------------------
            // VISITOR BREAKDOWN
            // Visitor breakdown charts use visit events only.
            // ----------------------------------------

            if (
                event.event_type === "visit"
            ) {

                const browser =
                    detectBrowser(
                        event.user_agent
                    );

                browserCounts[browser] =
                    (
                        browserCounts[browser]
                        || 0
                    ) + 1;


                const device =
                    detectDevice(
                        event.user_agent
                    );

                deviceCounts[device] =
                    (
                        deviceCounts[device]
                        || 0
                    ) + 1;


                const operatingSystem =
                    detectOperatingSystem(
                        event.user_agent
                    );

                osCounts[operatingSystem] =
                    (
                        osCounts[operatingSystem]
                        || 0
                    ) + 1;


                const referrer =
                    event.referrer
                        ? formatReferrer(
                            event.referrer
                        )
                        : "Direct";

                referrerCounts[referrer] =
                    (
                        referrerCounts[referrer]
                        || 0
                    ) + 1;


                const source =
                    detectTrafficSource(
                        event.referrer
                    );

                trafficSourceCounts[source] =
                    (
                        trafficSourceCounts[source]
                        || 0
                    ) + 1;

            }

        }
    );


    // ========================================
    // SORT DATES
    // ========================================

    const dateKeys =
        Object.keys({
            ...visitsByDate,
            ...clicksByDate
        });

    const sortedDates =
        dateKeys.sort(
            (a, b) =>
                new Date(a)
                -
                new Date(b)
        );


    // ========================================
    // DESTROY OLD CHARTS
    // ========================================

    if (visitsChart) {
        visitsChart.destroy();
    }

    if (clicksChart) {
        clicksChart.destroy();
    }

    if (linkClicksChart) {
        linkClicksChart.destroy();
    }

    if (activityHourChart) {
        activityHourChart.destroy();
    }

    if (browserChart) {
        browserChart.destroy();
    }

    if (deviceChart) {
        deviceChart.destroy();
    }

    if (osChart) {
        osChart.destroy();
    }

    if (referrerChart) {
        referrerChart.destroy();
    }

    if (visitorTypeChart) {
        visitorTypeChart.destroy();
    }

    if (trafficSourceChart) {
        trafficSourceChart.destroy();
    }


    // ========================================
    // COMMON OPTIONS
    // ========================================

    const commonOptions = {

        responsive: true,

        maintainAspectRatio: false,

        plugins: {

            legend: {

                display: false

            }

        },

        scales: {

            x: {

                ticks: {

                    color: "#9698a2"

                },

                grid: {

                    color:
                        "rgba(255,255,255,0.05)"

                }

            },

            y: {

                beginAtZero: true,

                ticks: {

                    color: "#9698a2",

                    precision: 0

                },

                grid: {

                    color:
                        "rgba(255,255,255,0.05)"

                }

            }

        }

    };


    // ========================================
    // VISITS OVER TIME
    // ========================================

    visitsChart =
        new Chart(
            document.getElementById(
                "visitsChart"
            ),
            {

                type: "line",

                data: {

                    labels: sortedDates,

                    datasets: [{

                        label: "Visits",

                        data:
                            sortedDates.map(
                                date =>
                                    visitsByDate[
                                        date
                                    ] || 0
                            ),

                        tension: 0.35,

                        borderWidth: 2,

                        fill: false

                    }]

                },

                options:
                    commonOptions

            }
        );


    // ========================================
    // CLICKS OVER TIME
    // ========================================

    clicksChart =
        new Chart(
            document.getElementById(
                "clicksChart"
            ),
            {

                type: "line",

                data: {

                    labels: sortedDates,

                    datasets: [{

                        label: "Clicks",

                        data:
                            sortedDates.map(
                                date =>
                                    clicksByDate[
                                        date
                                    ] || 0
                            ),

                        tension: 0.35,

                        borderWidth: 2,

                        fill: false

                    }]

                },

                options:
                    commonOptions

            }
        );


    // ========================================
    // CLICKS BY LINK
    // ========================================

    const linkLabels =
        Object.keys(
            clicksByLink
        );

    const linkValues =
        linkLabels.map(
            link =>
                clicksByLink[link]
        );

    linkClicksChart =
        new Chart(
            document.getElementById(
                "linkClicksChart"
            ),
            {

                type: "bar",

                data: {

                    labels:
                        linkLabels,

                    datasets: [{

                        label: "Clicks",

                        data:
                            linkValues,

                        borderRadius: 7,

                        borderWidth: 0

                    }]

                },

                options:
                    commonOptions

            }
        );


    // ========================================
    // ACTIVITY BY HOUR
    // ========================================

    activityHourChart =
        new Chart(
            document.getElementById(
                "activityHourChart"
            ),
            {

                type: "bar",

                data: {

                    labels:
                        activityByHour.map(
                            (_, hour) =>
                                `${String(hour).padStart(2, "0")}:00`
                        ),

                    datasets: [{

                        label: "Activity",

                        data:
                            activityByHour,

                        borderRadius: 5,

                        borderWidth: 0

                    }]

                },

                options:
                    commonOptions

            }
        );


    // ========================================
    // BROWSER BREAKDOWN
    // ========================================

    browserChart =
        new Chart(
            document.getElementById(
                "browserChart"
            ),
            {

                type: "doughnut",

                data: {

                    labels:
                        Object.keys(
                            browserCounts
                        ),

                    datasets: [{

                        data:
                            Object.values(
                                browserCounts
                            ),

                        borderWidth: 0

                    }]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: "bottom",

                            labels: {

                                color:
                                    "#9698a2"

                            }

                        }

                    }

                }

            }
        );


    // ========================================
    // DEVICE BREAKDOWN
    // ========================================

    deviceChart =
        new Chart(
            document.getElementById(
                "deviceChart"
            ),
            {

                type: "doughnut",

                data: {

                    labels:
                        Object.keys(
                            deviceCounts
                        ),

                    datasets: [{

                        data:
                            Object.values(
                                deviceCounts
                            ),

                        borderWidth: 0

                    }]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: "bottom",

                            labels: {

                                color:
                                    "#9698a2"

                            }

                        }

                    }

                }

            }
        );


    // ========================================
    // OPERATING SYSTEM
    // ========================================

    osChart =
        new Chart(
            document.getElementById(
                "osChart"
            ),
            {

                type: "doughnut",

                data: {

                    labels:
                        Object.keys(
                            osCounts
                        ),

                    datasets: [{

                        data:
                            Object.values(
                                osCounts
                            ),

                        borderWidth: 0

                    }]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: "bottom",

                            labels: {

                                color:
                                    "#9698a2"

                            }

                        }

                    }

                }

            }
        );


    // ========================================
    // REFERRER
    // ========================================

    referrerChart =
        new Chart(
            document.getElementById(
                "referrerChart"
            ),
            {

                type: "doughnut",

                data: {

                    labels:
                        Object.keys(
                            referrerCounts
                        ),

                    datasets: [{

                        data:
                            Object.values(
                                referrerCounts
                            ),

                        borderWidth: 0

                    }]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: "bottom",

                            labels: {

                                color:
                                    "#9698a2"

                            }

                        }

                    }

                }

            }
        );


    // ========================================
    // VISITOR TYPE
    // ========================================

    visitorTypeChart =
        new Chart(
            document.getElementById(
                "visitorTypeChart"
            ),
            {

                type: "doughnut",

                data: {

                    labels:
                        Object.keys(
                            visitorTypeCounts
                        ),

                    datasets: [{

                        data:
                            Object.values(
                                visitorTypeCounts
                            ),

                        borderWidth: 0

                    }]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: "bottom",

                            labels: {

                                color:
                                    "#9698a2"

                            }

                        }

                    }

                }

            }
        );


    // ========================================
    // TRAFFIC SOURCE
    // ========================================

    trafficSourceChart =
        new Chart(
            document.getElementById(
                "trafficSourceChart"
            ),
            {

                type: "doughnut",

                data: {

                    labels:
                        Object.keys(
                            trafficSourceCounts
                        ),

                    datasets: [{

                        data:
                            Object.values(
                                trafficSourceCounts
                            ),

                        borderWidth: 0

                    }]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            position: "bottom",

                            labels: {

                                color:
                                    "#9698a2"

                            }

                        }

                    }

                }

            }

        );

}
// ========================================
// LOADING STATE
// ========================================

function setLoadingState(
    loading
) {

    const refreshButton =
        document.getElementById(
            "refreshButton"
        );

    const clearButton =
        document.getElementById(
            "clearAnalyticsButton"
        );

    if (loading) {

        refreshButton.disabled =
            true;

        clearButton.disabled =
            true;

        refreshButton.textContent =
            "Refreshing...";

    } else {

        refreshButton.disabled =
            false;

        clearButton.disabled =
            false;

        refreshButton.textContent =
            "Refresh Analytics";
    }
}

// ========================================
// LIVE ANALYTICS
// ========================================

let refreshTimer = null;

let refreshInterval = 5000;

let lastSeenEventId = null;

let firstActivityLoad = true;


// ========================================
// SHOW NEW ACTIVITY
// ========================================

function showNewActivity() {

    const indicator =
        document.getElementById(
            "newActivity"
        );

    if (!indicator) {
        return;
    }

    indicator.classList.add(
        "show"
    );


    setTimeout(() => {

        indicator.classList.remove(
            "show"
        );

    }, 4000);

}


// ========================================
// CHECK FOR NEW ACTIVITY
// ========================================

function checkForNewActivity(
    events
) {

    if (
        !Array.isArray(events)
        ||
        events.length === 0
    ) {

        return;

    }


    // Recent activity is ordered
    // newest first.

    const latestEventId =
        events[0].id;


    // First dashboard load should
    // establish the baseline only.

    if (firstActivityLoad) {

        lastSeenEventId =
            latestEventId;

        firstActivityLoad = false;

        return;

    }


    // Detect a newer event.

    if (
        latestEventId !== null
        &&
        lastSeenEventId !== null
        &&
        latestEventId > lastSeenEventId
    ) {

        showNewActivity();

    }


    lastSeenEventId =
        latestEventId;

}


// ========================================
// START AUTO REFRESH
// ========================================

function startAutoRefresh() {

    if (refreshTimer) {

        clearInterval(
            refreshTimer
        );

        refreshTimer = null;

    }


    if (
        refreshInterval <= 0
    ) {

        return;

    }


    refreshTimer =
        setInterval(
            () => {

                loadDashboard();

            },
            refreshInterval
        );

}


// ========================================
// REFRESH INTERVAL CONTROL
// ========================================

document.getElementById(
    "refreshInterval"
).addEventListener(
    "change",
    function () {

        refreshInterval =
            Number(
                this.value
            );


        startAutoRefresh();

    }
);


// ========================================
// MANUAL REFRESH
// ========================================

document.getElementById(
    "refreshButton"
).addEventListener(
    "click",
    async function () {

        const button =
            this;


        const originalText =
            button.textContent;


        button.textContent =
            "Refreshing...";


        button.disabled =
            true;


        try {

            await loadDashboard();

        } finally {

            button.textContent =
                originalText;

            button.disabled =
                false;

        }

    }
);

// ========================================
// PHASE 6 — LINK MANAGEMENT
// ========================================

let managedLinks = [];


// ========================================
// LOAD LINK MANAGER
// ========================================

async function loadLinkManager() {

    const container =
        document.getElementById(
            "linkManagerList"
        );

    if (!container) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/admin/links"
            );

        if (response.status === 401) {

            window.location.href =
                "/admin/login";

            return;
        }

        if (!response.ok) {

            throw new Error(
                "Unable to load links."
            );

        }

        const data =
            await response.json();

        managedLinks =
            data.links || [];

        renderLinkManager();

    } catch (error) {

        console.error(
            "Link manager error:",
            error
        );

        container.innerHTML = `
            <div class="empty error">
                Unable to load links.
            </div>
        `;
    }
}


// ========================================
// RENDER LINK MANAGER
// ========================================

function renderLinkManager() {

    const container =
        document.getElementById(
            "linkManagerList"
        );

    if (!managedLinks.length) {

        container.innerHTML = `
            <div class="empty">
                No links available.
            </div>
        `;

        return;
    }

    container.innerHTML =
        managedLinks
            .map(
                (link, index) => {

                    const enabledBadge =
                        link.enabled
                            ? `
                                <span
                                    class="link-manager-badge enabled"
                                >
                                    Enabled
                                </span>
                            `
                            : `
                                <span
                                    class="link-manager-badge disabled"
                                >
                                    Disabled
                                </span>
                            `;

                    const featuredBadge =
                        link.featured
                            ? `
                                <span
                                    class="link-manager-badge featured"
                                >
                                    ★ Featured
                                </span>
                            `
                            : "";

                    return `
                        <div
                            class="link-manager-item"
                        >

                            <div
                                class="link-manager-main"
                            >

                                <div
                                    class="link-manager-name-row"
                                >

                                    <span
                                        class="link-manager-name"
                                    >
                                        ${escapeHtml(
                                            link.name
                                        )}
                                    </span>

                                </div>


                                <div
                                    class="link-manager-url"
                                    title="${escapeHtml(
                                        link.url
                                    )}"
                                >
                                    ${escapeHtml(
                                        link.url
                                    )}
                                </div>


                                <div
                                    class="link-manager-badges"
                                >

                                    ${enabledBadge}

                                    ${featuredBadge}

                                </div>

                            </div>


                            <div
                                class="link-manager-actions"
                            >

                                <button
                                    type="button"
                                    class="link-manager-action"
                                    onclick="moveManagedLink(
                                        ${link.id},
                                        -1
                                    )"
                                    ${index === 0
                                        ? "disabled"
                                        : ""}
                                    title="Move up"
                                >
                                    ↑
                                </button>


                                <button
                                    type="button"
                                    class="link-manager-action"
                                    onclick="moveManagedLink(
                                        ${link.id},
                                        1
                                    )"
                                    ${index === managedLinks.length - 1
                                        ? "disabled"
                                        : ""}
                                    title="Move down"
                                >
                                    ↓
                                </button>


                                <button
                                    type="button"
                                    class="link-manager-action"
                                    onclick="toggleManagedLink(
                                        ${link.id}
                                    )"
                                    title="Enable / Disable"
                                >
                                    ${link.enabled
                                        ? "Off"
                                        : "On"}
                                </button>


                                <button
                                    type="button"
                                    class="link-manager-action"
                                    onclick="toggleFeaturedLink(
                                        ${link.id}
                                    )"
                                    title="Toggle featured"
                                >
                                    ★
                                </button>


                                <button
                                    type="button"
                                    class="link-manager-action"
                                    onclick="editManagedLink(
                                        ${link.id}
                                    )"
                                    title="Edit"
                                >
                                    Edit
                                </button>


                                <button
                                    type="button"
                                    class="link-manager-action danger"
                                    onclick="deleteManagedLink(
                                        ${link.id}
                                    )"
                                    title="Delete"
                                >
                                    Delete
                                </button>

                            </div>

                        </div>
                    `;
                }
            )
            .join("");
}


// ========================================
// OPEN ADD LINK
// ========================================

function openAddLinkModal() {

    document.getElementById(
        "linkManagerModalTitle"
    ).textContent = "Add Link";

    document.getElementById(
        "linkManagerId"
    ).value = "";

    document.getElementById(
        "linkManagerName"
    ).value = "";

    document.getElementById(
        "linkManagerUrl"
    ).value = "";

    document.getElementById(
        "linkManagerDescription"
    ).value = "";

    document.getElementById(
        "linkManagerEnabled"
    ).checked = true;

    document.getElementById(
        "linkManagerFeatured"
    ).checked = false;

    document.getElementById(
        "linkManagerModal"
    ).hidden = false;

}


// ========================================
// OPEN EDIT LINK
// ========================================

function editManagedLink(id) {

    const link =
        managedLinks.find(
            item => item.id === id
        );

    if (!link) {
        return;
    }

    document.getElementById(
        "linkManagerModalTitle"
    ).textContent = "Edit Link";

    document.getElementById(
        "linkManagerId"
    ).value = link.id;

    document.getElementById(
        "linkManagerName"
    ).value = link.name || "";

    document.getElementById(
        "linkManagerUrl"
    ).value = link.url || "";

    document.getElementById(
        "linkManagerDescription"
    ).value =
        link.description || "";

    document.getElementById(
        "linkManagerEnabled"
    ).checked =
        Boolean(link.enabled);

    document.getElementById(
        "linkManagerFeatured"
    ).checked =
        Boolean(link.featured);

    document.getElementById(
        "linkManagerModal"
    ).hidden = false;
}


// ========================================
// CLOSE MODAL
// ========================================

function closeLinkManagerModal() {

    document.getElementById(
        "linkManagerModal"
    ).hidden = true;

}


// ========================================
// SAVE LINK
// ========================================

async function saveManagedLink(
    event
) {

    event.preventDefault();

    const saveButton =
        document.getElementById(
            "saveLinkButton"
        );

    const id =
        document.getElementById(
            "linkManagerId"
        ).value;

    const payload = {

        name:
            document.getElementById(
                "linkManagerName"
            ).value.trim(),

        url:
            document.getElementById(
                "linkManagerUrl"
            ).value.trim(),

        description:
            document.getElementById(
                "linkManagerDescription"
            ).value.trim(),

        enabled:
            document.getElementById(
                "linkManagerEnabled"
            ).checked,

        featured:
            document.getElementById(
                "linkManagerFeatured"
            ).checked

    };


    saveButton.disabled = true;

    saveButton.textContent =
        "Saving...";


    try {

        const response =
            await fetch(
                id
                    ? `/api/admin/links/${id}`
                    : "/api/admin/links",
                {
                    method:
                        id
                            ? "PUT"
                            : "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        if (response.status === 401) {

            window.location.href =
                "/admin/login";

            return;
        }


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Unable to save link."
            );

        }


        closeLinkManagerModal();

        await loadLinkManager();

        await loadDashboard();

    } catch (error) {

        console.error(
            "Save link error:",
            error
        );

        alert(
            error.message ||
            "Unable to save link."
        );

    } finally {

        saveButton.disabled = false;

        saveButton.textContent =
            "Save Link";

    }
}


// ========================================
// TOGGLE ENABLED
// ========================================

async function toggleManagedLink(id) {

    const link =
        managedLinks.find(
            item => item.id === id
        );

    if (!link) {
        return;
    }

    await updateManagedLink(
        id,
        {
            name: link.name,
            url: link.url,
            description:
                link.description || "",
            enabled:
                !Boolean(link.enabled),
            featured:
                Boolean(link.featured)
        }
    );
}


// ========================================
// TOGGLE FEATURED
// ========================================

async function toggleFeaturedLink(id) {

    const link =
        managedLinks.find(
            item => item.id === id
        );

    if (!link) {
        return;
    }

    await updateManagedLink(
        id,
        {
            name: link.name,
            url: link.url,
            description:
                link.description || "",
            enabled:
                Boolean(link.enabled),
            featured:
                !Boolean(link.featured)
        }
    );
}


// ========================================
// UPDATE LINK HELPER
// ========================================

async function updateManagedLink(
    id,
    payload
) {

    try {

        const response =
            await fetch(
                `/api/admin/links/${id}`,
                {
                    method: "PUT",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Unable to update link."
            );

        }


        await loadLinkManager();

        await loadDashboard();

    } catch (error) {

        console.error(
            "Update link error:",
            error
        );

        alert(
            error.message ||
            "Unable to update link."
        );

    }
}


// ========================================
// DELETE LINK
// ========================================

async function deleteManagedLink(id) {

    const link =
        managedLinks.find(
            item => item.id === id
        );

    if (!link) {
        return;
    }


    const confirmed =
        window.confirm(
            `Delete "${link.name}"?\n\n`
            + "Its existing analytics history "
            + "will remain in the database."
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/admin/links/${id}`,
                {
                    method: "DELETE"
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Unable to delete link."
            );

        }


        await loadLinkManager();

        await loadDashboard();

    } catch (error) {

        console.error(
            "Delete link error:",
            error
        );

        alert(
            error.message ||
            "Unable to delete link."
        );

    }
}


// ========================================
// MOVE LINK
// ========================================

async function moveManagedLink(
    id,
    direction
) {

    const currentIndex =
        managedLinks.findIndex(
            item => item.id === id
        );

    if (currentIndex === -1) {
        return;
    }

    const newIndex =
        currentIndex + direction;

    if (
        newIndex < 0 ||
        newIndex >= managedLinks.length
    ) {
        return;
    }


    const reordered =
        [...managedLinks];


    const [moved] =
        reordered.splice(
            currentIndex,
            1
        );


    reordered.splice(
        newIndex,
        0,
        moved
    );


    const linkIds =
        reordered.map(
            item => item.id
        );


    try {

        const response =
            await fetch(
                "/api/admin/links/reorder",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            link_ids:
                                linkIds
                        })
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Unable to reorder links."
            );

        }


        await loadLinkManager();

    } catch (error) {

        console.error(
            "Reorder error:",
            error
        );

        alert(
            error.message ||
            "Unable to reorder links."
        );
    }
}


// ========================================
// LINK MANAGER EVENTS
// ========================================

document.getElementById(
    "addLinkButton"
).addEventListener(
    "click",
    openAddLinkModal
);


document.getElementById(
    "closeLinkModalButton"
).addEventListener(
    "click",
    closeLinkManagerModal
);


document.getElementById(
    "cancelLinkButton"
).addEventListener(
    "click",
    closeLinkManagerModal
);


document.getElementById(
    "linkManagerForm"
).addEventListener(
    "submit",
    saveManagedLink
);


document.getElementById(
    "linkManagerModal"
).addEventListener(
    "click",
    function (event) {

        if (
            event.target === this
        ) {
            closeLinkManagerModal();
        }

    }
);


// Initial manager load.
loadLinkManager();

// ========================================
// PHASE 7 — QR & CAMPAIGN ANALYTICS
// ========================================


let phase7QrCodes = [];

let phase7Campaigns = [];

let phase7Links = [];


// ========================================
// PHASE 7 — LOAD LINKS
// ========================================

async function loadPhase7Links() {

    const response =
        await fetch(
            "/api/admin/links"
        );

    if (
        response.status === 401
    ) {

        window.location.href =
            "/admin/login";

        return [];

    }

    if (!response.ok) {

        throw new Error(
            "Unable to load managed links."
        );

    }

    const data =
        await response.json();

    return data.links || [];
}


// ========================================
// PHASE 7 — MAIN QR
// ========================================

async function loadMainQr() {

    const response =
        await fetch(
            "/api/admin/qr/main"
        );

    if (
        response.status === 401
    ) {

        window.location.href =
            "/admin/login";

        return;
    }

    if (!response.ok) {

        throw new Error(
            "Unable to load main QR."
        );

    }

    const data =
        await response.json();

    const qr =
        data.qr;


    document.getElementById(
        "mainQrImage"
    ).src =
        qr.image_url;


    document.getElementById(
        "mainQrStatus"
    ).textContent =
        "Main Link Hub QR ready";


    document.getElementById(
        "mainQrUrl"
    ).textContent =
        qr.scan_url;


    document.getElementById(
        "mainQrOpen"
    ).href =
        qr.scan_url;


    document.getElementById(
        "mainQrDownload"
    ).href =
        qr.image_url
        + "?download=1";
}


// ========================================
// PHASE 7 — LOAD QR CODES
// ========================================

async function loadPhase7QrCodes() {

    const response =
        await fetch(
            "/api/admin/qr-codes"
        );

    if (
        response.status === 401
    ) {

        window.location.href =
            "/admin/login";

        return;

    }

    if (!response.ok) {

        throw new Error(
            "Unable to load QR codes."
        );

    }

    const data =
        await response.json();

    phase7QrCodes =
        data.qr_codes || [];

}


// ========================================
// PHASE 7 — RENDER LINK QR
// ========================================

function renderPhase7LinkQr() {

    const container =
        document.getElementById(
            "phase7LinkQrList"
        );


    if (!phase7Links.length) {

        container.innerHTML = `
            <div class="empty">
                No managed links available.
            </div>
        `;

        return;
    }


    container.innerHTML =
        phase7Links
            .map(
                link => {

                    const qr =
                        phase7QrCodes.find(
                            item =>
                                Number(
                                    item.link_id
                                ) ===
                                Number(
                                    link.id
                                )
                                &&
                                !item.campaign_id
                        );


                    return `
                        <div
                            class="phase7-item"
                        >

                            <div
                                class="phase7-item-main"
                            >

                                <div
                                    class="phase7-item-name"
                                >
                                    ${escapeHtml(
                                        link.icon ||
                                        "↗"
                                    )}
                                    ${escapeHtml(
                                        link.name
                                    )}
                                </div>

                                <div
                                    class="phase7-item-meta"
                                >

                                    <span>
                                        ${escapeHtml(
                                            link.url
                                        )}
                                    </span>

                                </div>

                                ${
                                    qr
                                        ? `
                                            <img
                                                class="phase7-qr-small"
                                                src="${escapeHtml(
                                                    qr.image_url
                                                )}"
                                                alt="QR code"
                                            >
                                        `
                                        : ""
                                }

                            </div>


                            <div
                                class="phase7-item-actions"
                            >

                                <button
                                    type="button"
                                    class="phase7-button"
                                    onclick="generateLinkQr(
                                        ${link.id}
                                    )"
                                >
                                    ${
                                        qr
                                            ? "Refresh QR"
                                            : "Generate QR"
                                    }
                                </button>

                                ${
                                    qr
                                        ? `
                                            <a
                                                class="phase7-button"
                                                href="${escapeHtml(
                                                    qr.image_url
                                                )}?download=1"
                                                target="_blank"
                                            >
                                                Download
                                            </a>
                                        `
                                        : ""
                                }

                            </div>

                        </div>
                    `;

                }
            )
            .join("");
}


// ========================================
// PHASE 7 — GENERATE INDIVIDUAL QR
// ========================================

async function generateLinkQr(
    linkId
) {

    try {

        const response =
            await fetch(
                `/api/admin/qr/link/${linkId}`
            );


        if (!response.ok) {

            const result =
                await response.json();

            throw new Error(
                result.error ||
                "Unable to generate QR."
            );

        }


        await loadPhase7QrCodes();

        renderPhase7LinkQr();

    } catch (error) {

        console.error(
            "QR generation error:",
            error
        );

        alert(
            error.message ||
            "Unable to generate QR."
        );

    }
}


// ========================================
// PHASE 7 — CAMPAIGN LINK SELECT
// ========================================

function renderCampaignLinkOptions() {

    const select =
        document.getElementById(
            "campaignLink"
        );


    select.innerHTML = `
        <option value="">
            Main Link Hub
        </option>
    `;


    phase7Links.forEach(
        link => {

            select.innerHTML += `
                <option
                    value="${escapeHtml(
                        link.id
                    )}"
                >
                    ${escapeHtml(
                        link.name
                    )}
                </option>
            `;

        }
    );

}


// ========================================
// PHASE 7 — LOAD CAMPAIGNS
// ========================================

async function loadPhase7Campaigns() {

    const response =
        await fetch(
            "/api/admin/campaigns"
        );


    if (
        response.status === 401
    ) {

        window.location.href =
            "/admin/login";

        return;

    }


    if (!response.ok) {

        throw new Error(
            "Unable to load campaigns."
        );

    }


    const data =
        await response.json();


    phase7Campaigns =
        data.campaigns || [];


    renderPhase7Campaigns();

}


// ========================================
// PHASE 7 — RENDER CAMPAIGNS
// ========================================

function renderPhase7Campaigns() {

    const container =
        document.getElementById(
            "campaignPerformanceList"
        );


    if (!phase7Campaigns.length) {

        container.innerHTML = `
            <div class="empty">
                No campaigns created yet.
            </div>
        `;

        return;
    }


    container.innerHTML =
        phase7Campaigns
            .map(
                campaign => `

                    <div
                        class="phase7-item"
                    >

                        <div
                            class="phase7-item-main"
                        >

                            <div
                                class="phase7-item-name"
                            >
                                ${escapeHtml(
                                    campaign.name
                                )}
                            </div>


                            <div
                                class="phase7-item-meta"
                            >

                                <span
                                    class="phase7-badge source"
                                >
                                    Source:
                                    ${escapeHtml(
                                        campaign.source
                                    )}
                                </span>

                                <span
                                    class="phase7-badge medium"
                                >
                                    Medium:
                                    ${escapeHtml(
                                        campaign.medium
                                    )}
                                </span>

                                <span>
                                    Destination:
                                    ${escapeHtml(
                                        campaign.link_name ||
                                        "Main Link Hub"
                                    )}
                                </span>

                                <span>
                                    ${
                                        campaign.clicks
                                    }
                                    ${
                                        Number(
                                            campaign.clicks
                                        ) === 1
                                            ? "click"
                                            : "clicks"
                                    }
                                </span>

                            </div>


                            ${
                                campaign.scan_url
                                    ? `
                                        <div
                                            class="phase7-qr-url"
                                        >
                                            ${escapeHtml(
                                                campaign.scan_url
                                            )}
                                        </div>
                                    `
                                    : ""
                            }

                        </div>


                        <div
                            class="phase7-item-actions"
                        >

                            ${
                                campaign.image_url
                                    ? `
                                        <a
                                            class="phase7-button"
                                            href="${escapeHtml(
                                                campaign.image_url
                                            )}?download=1"
                                            target="_blank"
                                        >
                                            Download QR
                                        </a>
                                    `
                                    : ""
                            }


                            ${
                                campaign.scan_url
                                    ? `
                                        <a
                                            class="phase7-button"
                                            href="${escapeHtml(
                                                campaign.scan_url
                                            )}"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            Open
                                        </a>
                                    `
                                    : ""
                            }


                            <button
                                type="button"
                                class="phase7-button danger"
                                onclick="deletePhase7Campaign(
                                    ${campaign.id}
                                )"
                            >
                                Delete
                            </button>

                        </div>

                    </div>

                `
            )
            .join("");

}


// ========================================
// PHASE 7 — CREATE CAMPAIGN
// ========================================

async function createPhase7Campaign(
    event
) {

    event.preventDefault();


    const button =
        document.getElementById(
            "createCampaignButton"
        );


    const payload = {

        name:
            document.getElementById(
                "campaignName"
            ).value.trim(),

        source:
            document.getElementById(
                "campaignSource"
            ).value.trim(),

        medium:
            document.getElementById(
                "campaignMedium"
            ).value.trim(),

        link_id:
            document.getElementById(
                "campaignLink"
            ).value || null

    };


    button.disabled = true;

    button.textContent =
        "Creating...";


    try {

        const response =
            await fetch(
                "/api/admin/campaigns",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Unable to create campaign."
            );

        }


        document.getElementById(
            "campaignForm"
        ).reset();


        await loadPhase7QrCodes();

        await loadPhase7Campaigns();


        alert(
            "Campaign created successfully."
        );


    } catch (error) {

        console.error(
            "Campaign creation error:",
            error
        );

        alert(
            error.message ||
            "Unable to create campaign."
        );


    } finally {

        button.disabled = false;

        button.textContent =
            "Create Campaign";

    }

}


// ========================================
// PHASE 7 — DELETE CAMPAIGN
// ========================================

async function deletePhase7Campaign(
    campaignId
) {

    const campaign =
        phase7Campaigns.find(
            item =>
                Number(item.id) ===
                Number(campaignId)
        );


    if (!campaign) {
        return;
    }


    const confirmed =
        window.confirm(
            `Delete campaign "${campaign.name}"?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/admin/campaigns/${campaignId}`,
                {
                    method: "DELETE"
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Unable to delete campaign."
            );

        }


        await loadPhase7QrCodes();

        await loadPhase7Campaigns();


    } catch (error) {

        console.error(
            "Campaign delete error:",
            error
        );

        alert(
            error.message ||
            "Unable to delete campaign."
        );

    }

}


// ========================================
// PHASE 7 — INITIAL LOAD
// ========================================

async function loadPhase7() {

    try {

        phase7Links =
            await loadPhase7Links();


        renderCampaignLinkOptions();


        await loadMainQr();

        await loadPhase7QrCodes();

        renderPhase7LinkQr();

        await loadPhase7Campaigns();


    } catch (error) {

        console.error(
            "Phase 7 error:",
            error
        );


        const qrList =
            document.getElementById(
                "phase7LinkQrList"
            );

        if (qrList) {

            qrList.innerHTML = `
                <div class="empty error">
                    Unable to load QR analytics.
                </div>
            `;

        }

    }

}


document.getElementById(
    "campaignForm"
).addEventListener(
    "submit",
    createPhase7Campaign
);


loadPhase7();

// ========================================
// PHASE 8 — REPORTS
// ========================================


function getReportDateRange() {

    return getTimeRange()

}


// ========================================
// ANALYTICS SUMMARY
// ========================================


async function loadReportSummary() {

    const range =
        getReportDateRange();


    if (
        !range ||
        !range.start ||
        !range.end
    ) {

        alert(
            "Please select an analytics period first."
        );

        return;

    }


    const button =
        document.getElementById(
            "loadReportSummaryButton"
        );


    const status =
        document.getElementById(
            "reportSummaryStatus"
        );


    button.disabled = true;

    button.textContent =
        "Loading...";


    status.textContent =
        "Generating analytics summary...";


    try {

        const response =
            await fetch(
                `/api/reports/summary?start=${encodeURIComponent(
                    range.start
                )}&end=${encodeURIComponent(
                    range.end
                )}`
            );


        if (
            response.status === 401
        ) {

            window.location.href =
                "/admin/login";

            return;

        }


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Unable to generate summary."
            );

        }


        const summary =
            data.summary;


        document.getElementById(
            "reportTotalEvents"
        ).textContent =
            summary.total_events ?? 0;


        document.getElementById(
            "reportTotalVisits"
        ).textContent =
            summary.total_visits ?? 0;


        document.getElementById(
            "reportTotalClicks"
        ).textContent =
            summary.total_clicks ?? 0;


        document.getElementById(
            "reportUniqueVisitors"
        ).textContent =
            summary.unique_visitors ?? 0;


        document.getElementById(
            "reportRepeatVisitors"
        ).textContent =
            summary.repeat_visitors ?? 0;


        document.getElementById(
            "reportClickRate"
        ).textContent =
            `${Number(
                summary.click_rate || 0
            ).toFixed(2)}%`;


        status.textContent =
            `Report generated for ${
                range.start
            } → ${
                range.end
            }.`;

    } catch (error) {

        console.error(
            "Report summary error:",
            error
        );


        status.textContent =
            error.message ||
            "Unable to generate summary.";

    } finally {

        button.disabled = false;

        button.textContent =
            "Generate Summary";

    }

}


// ========================================
// FILTERED CSV
// ========================================


function updateFilteredCsvLink() {

    const range =
        getReportDateRange();


    const button =
        document.getElementById(
            "exportFilteredCsvButton"
        );


    if (
        !range ||
        !range.start ||
        !range.end
    ) {

        button.href =
            "#";

        return;

    }


    button.href =
        `/api/export/csv/filtered?start=${encodeURIComponent(
            range.start
        )}&end=${encodeURIComponent(
            range.end
        )}`;

}


// ========================================
// MONTHLY REPORT
// ========================================


async function loadMonthlyReport() {

    const monthInput =
        document.getElementById(
            "reportMonth"
        );


    const month =
        monthInput.value;


    if (!month) {

        alert(
            "Please select a month."
        );

        return;

    }


    const button =
        document.getElementById(
            "loadMonthlyReportButton"
        );


    const status =
        document.getElementById(
            "monthlyReportStatus"
        );


    button.disabled = true;

    button.textContent =
        "Loading...";


    status.textContent =
        "Generating monthly report...";


    try {

        const response =
            await fetch(
                `/api/reports/monthly?month=${encodeURIComponent(
                    month
                )}`
            );


        if (
            response.status === 401
        ) {

            window.location.href =
                "/admin/login";

            return;

        }


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Unable to generate monthly report."
            );

        }


        const summary =
            data.summary;


        document.getElementById(
            "monthlyTotalEvents"
        ).textContent =
            summary.total_events ?? 0;


        document.getElementById(
            "monthlyTotalVisits"
        ).textContent =
            summary.total_visits ?? 0;


        document.getElementById(
            "monthlyTotalClicks"
        ).textContent =
            summary.total_clicks ?? 0;


        document.getElementById(
            "monthlyUniqueVisitors"
        ).textContent =
            summary.unique_visitors ?? 0;


        document.getElementById(
            "monthlyTopLink"
        ).textContent =
            summary.top_link?.name ||
            "No clicks";


        document.getElementById(
            "monthlyClickRate"
        ).textContent =
            `${Number(
                summary.click_rate || 0
            ).toFixed(2)}%`;


        document.getElementById(
            "downloadMonthlyPdfButton"
        ).href =
            `/api/reports/monthly/pdf?month=${encodeURIComponent(
                month
            )}`;


        status.textContent =
            `Monthly report generated for ${month}.`;

    } catch (error) {

        console.error(
            "Monthly report error:",
            error
        );


        status.textContent =
            error.message ||
            "Unable to generate monthly report.";

    } finally {

        button.disabled = false;

        button.textContent =
            "Generate";

    }

}


// ========================================
// REPORT EVENT LISTENERS
// ========================================


document.getElementById(
    "loadReportSummaryButton"
).addEventListener(
    "click",
    loadReportSummary
);


document.getElementById(
    "loadMonthlyReportButton"
).addEventListener(
    "click",
    loadMonthlyReport
);


// ========================================
// REPORT MONTH DEFAULT
// ========================================


const reportMonthInput =
    document.getElementById(
        "reportMonth"
    );


if (reportMonthInput) {

    const now =
        new Date();


    reportMonthInput.value =
        `${now.getFullYear()}-${
            String(
                now.getMonth() + 1
            ).padStart(2, "0")
        }`;

}


// ========================================
// FILTERED CSV UPDATE
// ========================================


document.getElementById(
    "timeRange"
).addEventListener(
    "change",
    updateFilteredCsvLink
);


updateFilteredCsvLink();
// ========================================
// INITIAL LOAD
// ========================================

loadDashboard();


// ========================================
// START AUTO REFRESH
// ========================================

startAutoRefresh();
