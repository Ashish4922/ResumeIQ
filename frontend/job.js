const API_URL = "http://127.0.0.1:8000";

const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "login.html";
}

const resumeFile = document.getElementById("resumeFile");
const fileName = document.getElementById("fileName");
const analyzeBtn = document.getElementById("analyzeBtn");
const jobDescription = document.getElementById("jobDescription");
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
        fileName.textContent =
            resumeFile.files[0].name;
    } else {
        fileName.textContent =
            "PDF, DOCX, TXT, PNG or JPG";
    }

});

analyzeBtn.addEventListener("click", function(event) {

    event.preventDefault();

    analyzeJob();

});

async function analyzeJob() {

    hideError();

    if (!resumeFile.files.length) {
        showError("Please select your resume.");
        return;
    }

    if (!jobDescription.value.trim()) {
        showError("Please paste the job description.");
        return;
    }

    const formData = new FormData();

    formData.append(
        "file",
        resumeFile.files[0]
    );

    formData.append(
        "job_description",
        jobDescription.value.trim()
    );

    setLoading(true);

    try {

        console.log("Starting job analysis...");

        const response = await fetch(
            `${API_URL}/analyze-job`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`
                },
                body: formData
            }
        );

        console.log(
            "Job analysis status:",
            response.status
        );

        const data = await response.json();

        console.log(
            "Job analysis response:",
            data
        );

        if (!response.ok) {

            if (response.status === 402) {

                showError(
                    "Your free credits are exhausted. Each additional analysis costs ₹10."
                );

            } else if (response.status === 401) {

                localStorage.removeItem("token");

                window.location.href =
                    "login.html";

            } else {

                const detail =
                    typeof data.detail === "string"
                        ? data.detail
                        : data.detail?.message;

                showError(
                    detail || "Job analysis failed."
                );
            }

            return;
        }

        if (!data.analysis) {

            showError(
                "The backend returned no analysis data."
            );

            console.error(
                "Missing analysis:",
                data
            );

            return;
        }

        displayResults(
            data.analysis
        );

        if (
            data.credit &&
            data.credit.remaining_free !== undefined
        ) {

            document.getElementById(
                "freeCredits"
            ).textContent =
                data.credit.remaining_free;
        }

        resultsSection.classList.remove(
            "hidden"
        );

        console.log(
            "Results section displayed."
        );

        setTimeout(() => {

            resultsSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }, 100);

    } catch (error) {

        console.error(
            "Job analysis error:",
            error
        );

        showError(
            "An error occurred while analyzing the job description."
        );

    } finally {

        setLoading(false);

    }
}

function displayResults(analysis) {

    document.getElementById(
        "matchScore"
    ).textContent =
        analysis.match_score ?? 0;

    document.getElementById(
        "matchSummary"
    ).textContent =
        analysis.summary || "-";

    renderTags(
        "matchedSkills",
        analysis.matched_skills || []
    );

    renderTags(
        "missingSkills",
        analysis.missing_skills || []
    );

    renderList(
        "matchedRequirements",
        analysis.matched_requirements || []
    );

    renderList(
        "missingRequirements",
        analysis.missing_requirements || []
    );

    renderList(
        "recommendations",
        analysis.recommendations || []
    );

    renderSkillUpgrades(
        analysis.skill_upgrades || []
    );
}

function renderTags(elementId, items) {

    const element =
        document.getElementById(elementId);

    if (!element) {
        return;
    }

    element.innerHTML = "";

    if (
        !Array.isArray(items) ||
        items.length === 0
    ) {

        const tag =
            document.createElement("span");

        tag.className = "tag";

        tag.textContent =
            "None found";

        element.appendChild(tag);

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

function renderList(elementId, items) {

    const element =
        document.getElementById(elementId);

    if (!element) {
        return;
    }

    element.innerHTML = "";

    if (
        !Array.isArray(items) ||
        items.length === 0
    ) {

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

function renderSkillUpgrades(items) {

    const container =
        document.getElementById(
            "skillUpgrades"
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (
        !Array.isArray(items) ||
        items.length === 0
    ) {

        container.textContent =
            "No skill upgrades recommended.";

        return;
    }

    items.forEach(item => {

        const card =
            document.createElement("div");

        card.className =
            "skill-upgrade";

        const priority =
            item.priority || "Medium";

        card.innerHTML = `
            <div class="skill-top">
                <h4>${escapeHtml(
                    item.skill || "Skill"
                )}</h4>

                <span class="priority ${escapeHtml(
                    priority.toLowerCase()
                )}">
                    ${escapeHtml(priority)}
                </span>
            </div>

            <p>
                ${escapeHtml(
                    item.reason ||
                    "No reason provided."
                )}
            </p>
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

        loading.classList.remove(
            "hidden"
        );

        analyzeBtn.disabled = true;

        analyzeBtn.textContent =
            "Analyzing...";

    } else {

        loading.classList.add(
            "hidden"
        );

        analyzeBtn.disabled = false;

        analyzeBtn.textContent =
            "Analyze Job Match";
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
    function() {

        localStorage.removeItem(
            "token"
        );

        window.location.href =
            "login.html";

    }
);

newAnalysisBtn.addEventListener(
    "click",
    function() {

        resultsSection.classList.add(
            "hidden"
        );

        resumeFile.value = "";

        fileName.textContent =
            "PDF, DOCX, TXT, PNG or JPG";

        jobDescription.value = "";

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    }
);

loadUser();