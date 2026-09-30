const API_URL = "http://127.0.0.1:8000";

const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "login.html";
}

const resumeFile = document.getElementById("resumeFile");
const fileName = document.getElementById("fileName");
const analyzeBtn = document.getElementById("analyzeBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");
const resultsSection = document.getElementById("resultsSection");
const logoutBtn = document.getElementById("logoutBtn");
const newAnalysisBtn = document.getElementById("newAnalysisBtn");

async function loadUser() {
    try {
        const response = await fetch(`${API_URL}/me`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (!response.ok) {
            localStorage.removeItem("token");
            window.location.href = "login.html";
            return;
        }

        const user = await response.json();

        document.getElementById("userName").textContent =
            user.name || "User";

        document.getElementById("freeCredits").textContent =
            user.free_credits ?? 0;

    } catch (error) {
        showError("Could not connect to the backend.");
    }
}

resumeFile.addEventListener("change", () => {
    if (resumeFile.files.length > 0) {
        fileName.textContent = resumeFile.files[0].name;
    } else {
        fileName.textContent = "No file selected";
    }
});

analyzeBtn.addEventListener("click", analyzeResume);

async function analyzeResume() {
    hideError();

    if (!resumeFile.files.length) {
        showError("Please select a resume first.");
        return;
    }

    const file = resumeFile.files[0];

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);

    try {
        const response = await fetch(
            `${API_URL}/analyze-resume`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`
                },
                body: formData
            }
        );

        const data = await response.json();

        console.log("ResumeIQ API response:", data);
        console.log("HTTP status:", response.status);

        if (!response.ok) {
            if (response.status === 402) {
                showError(
                    "Your free credits are exhausted. Each additional analysis costs ₹10."
                );
            } else if (response.status === 401) {
                localStorage.removeItem("token");
                window.location.href = "login.html";
            } else {
                const detail =
                    typeof data.detail === "string"
                        ? data.detail
                        : data.detail?.message;

                showError(
                    detail || "Resume analysis failed."
                );
            }

            return;
        }

        if (!data.analysis) {
            showError(
                "The backend returned no analysis data."
            );
            console.error(
                "Missing analysis field:",
                data
            );
            return;
        }

        displayResults(data.analysis);

        if (data.credit) {
            if (
                data.credit.remaining_free !== undefined
            ) {
                document.getElementById(
                    "freeCredits"
                ).textContent =
                    data.credit.remaining_free;
            }
        }

        resultsSection.classList.remove("hidden");

        setTimeout(() => {
            resultsSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }, 100);

    } catch (error) {
        console.error(
            "Resume analysis error:",
            error
        );

        showError(
            "An error occurred while displaying the resume analysis. Check the browser Console."
        );
    } finally {
        setLoading(false);
    }
}

function displayResults(analysis) {
    const candidate =
        analysis.candidate || {};

    const quality =
        analysis.resume_quality || {};

    const ats =
        analysis.ats_analysis || {};

    const upgrades =
        analysis.skill_upgrades || [];

    document.getElementById(
        "resumeScore"
    ).textContent =
        quality.score ?? 0;

    document.getElementById(
        "atsScore"
    ).textContent =
        ats.score ?? 0;

    document.getElementById(
        "candidateName"
    ).textContent =
        candidate.name || "-";

    document.getElementById(
        "candidateEmail"
    ).textContent =
        candidate.email || "-";

    document.getElementById(
        "candidatePhone"
    ).textContent =
        candidate.phone || "-";

    document.getElementById(
        "candidateLocation"
    ).textContent =
        candidate.location || "-";

    renderList(
        "educationList",
        candidate.education || []
    );

    renderList(
        "experienceList",
        candidate.experience || []
    );

    renderTags(
        "technicalSkills",
        candidate.technical_skills || []
    );

    renderTags(
        "softSkills",
        candidate.soft_skills || []
    );

    renderList(
        "strengthsList",
        quality.strengths || []
    );

    renderList(
        "weaknessesList",
        quality.weaknesses || []
    );

    renderList(
        "resumeSuggestions",
        quality.suggestions || []
    );

    renderList(
        "atsIssues",
        ats.issues || []
    );

    renderTags(
        "keywordsFound",
        ats.keywords_found || []
    );

    renderTags(
        "missingKeywords",
        ats.missing_keywords || []
    );

    renderList(
        "atsSuggestions",
        ats.suggestions || []
    );

    renderSkillUpgrades(upgrades);
}

function renderList(elementId, items) {
    const element =
        document.getElementById(elementId);

    if (!element) {
        console.error(
            `Element not found: ${elementId}`
        );
        return;
    }

    element.innerHTML = "";

    if (!Array.isArray(items) || items.length === 0) {
        const li =
            document.createElement("li");

        li.textContent =
            "No information found.";

        element.appendChild(li);
        return;
    }

    items.forEach(item => {
        const li =
            document.createElement("li");

        li.textContent =
            String(item);

        element.appendChild(li);
    });
}

function renderTags(elementId, items) {
    const element =
        document.getElementById(elementId);

    if (!element) {
        console.error(
            `Element not found: ${elementId}`
        );
        return;
    }

    element.innerHTML = "";

    if (!Array.isArray(items) || items.length === 0) {
        const span =
            document.createElement("span");

        span.className = "tag";

        span.textContent =
            "None found";

        element.appendChild(span);
        return;
    }

    items.forEach(item => {
        const tag =
            document.createElement("span");

        tag.className = "tag";

        tag.textContent =
            String(item);

        element.appendChild(tag);
    });
}

function renderSkillUpgrades(upgrades) {
    const container =
        document.getElementById(
            "skillUpgrades"
        );

    if (!container) {
        console.error(
            "Element not found: skillUpgrades"
        );
        return;
    }

    container.innerHTML = "";

    if (
        !Array.isArray(upgrades) ||
        upgrades.length === 0
    ) {
        container.textContent =
            "No skill upgrades recommended.";

        return;
    }

    upgrades.forEach(item => {
        const card =
            document.createElement("div");

        card.className =
            "skill-upgrade";

        const skill =
            item.skill || "Recommended Skill";

        const reason =
            item.reason || "No reason provided.";

        const priority =
            item.priority || "Medium";

        const priorityClass =
            String(priority).toLowerCase();

        card.innerHTML = `
            <div class="skill-top">
                <h4>${escapeHtml(skill)}</h4>
                <span class="priority ${escapeHtml(priorityClass)}">
                    ${escapeHtml(priority)}
                </span>
            </div>
            <p>${escapeHtml(reason)}</p>
        `;

        container.appendChild(card);
    });
}

function escapeHtml(value) {
    const div =
        document.createElement("div");

    div.textContent =
        String(value ?? "");

    return div.innerHTML;
}

function setLoading(status) {
    if (status) {
        loading.classList.remove("hidden");

        analyzeBtn.disabled = true;

        analyzeBtn.textContent =
            "Analyzing...";
    } else {
        loading.classList.add("hidden");

        analyzeBtn.disabled = false;

        analyzeBtn.textContent =
            "Analyze Resume";
    }
}

function showError(message) {
    errorMessage.textContent =
        message;

    errorMessage.classList.remove(
        "hidden"
    );
}

function hideError() {
    errorMessage.textContent = "";

    errorMessage.classList.add(
        "hidden"
    );
}

logoutBtn.addEventListener(
    "click",
    () => {
        localStorage.removeItem("token");

        window.location.href =
            "login.html";
    }
);

newAnalysisBtn.addEventListener(
    "click",
    () => {
        resultsSection.classList.add(
            "hidden"
        );

        resumeFile.value = "";

        fileName.textContent =
            "No file selected";

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }
);

loadUser();