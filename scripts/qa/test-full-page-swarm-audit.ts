import * as fs from "fs";
import * as path from "path";

const indexHtmlPath = path.resolve(__dirname, "../../frontend/archive/unused_views.html");
const appJsPath = path.resolve(__dirname, "../../frontend/archive/unused_views.js");

function runAudit() {
  console.log("==================================================");
  console.log("STARTING FULL-PAGE SWARM VIEW & NAV INVENTORY AUDIT");
  console.log("==================================================");

  const errors: string[] = [];
  const findings: string[] = [];

  if (!fs.existsSync(indexHtmlPath)) {
    errors.push("frontend/index.html not found");
    return writeReport(errors, findings);
  }
  if (!fs.existsSync(appJsPath)) {
    errors.push("frontend/app.js not found");
    return writeReport(errors, findings);
  }

  const html = fs.readFileSync(indexHtmlPath, "utf-8");
  const js = fs.readFileSync(appJsPath, "utf-8");

  // Check required views and nav links
  const requiredNavViewPairs = [
    { nav: ["nav-readiness-autopilot"], view: ["view-readiness-autopilot"] },
    { nav: ["nav-hochster-runtime", "nav-hochster"], view: ["view-hochster-runtime", "view-hochster"] },
    { nav: ["nav-cybersecurity-factory"], view: ["view-cybersecurity-factory"] },
    { nav: ["nav-remediation-safety"], view: ["view-remediation-safety"] },
    { nav: ["nav-runtime-audit"], view: ["view-runtime-audit"] },
    { nav: ["nav-error-budget"], view: ["view-error-budget"] },
    { nav: ["nav-release-provenance"], view: ["view-release-provenance"] },
    { nav: ["nav-swarm-control"], view: ["view-swarm-control"] },
    { nav: ["nav-mission-intel"], view: ["view-mission", "view-mission-intel"] },
    { nav: ["nav-timeline-replay"], view: ["view-replay", "view-timeline-replay"] }
  ];

  requiredNavViewPairs.forEach(({ nav, view }) => {
    const hasNav = nav.some(n => html.includes(`id="${n}"`) || html.includes(`id='${n}'`));
    if (hasNav) {
      findings.push(`Nav ID checked: ${nav.join(" or ")}`);
    } else {
      errors.push(`Missing Nav ID in HTML: ${nav.join(" or ")}`);
    }

    const hasView = view.some(v => html.includes(`id="${v}"`) || html.includes(`id='${v}'`));
    if (hasView) {
      findings.push(`View ID checked: ${view.join(" or ")}`);
    } else {
      errors.push(`Missing View ID in HTML: ${view.join(" or ")}`);
    }
  });

  // Verify elements
  const requiredElements = [
    "topology-agent-overlay-runtime",
    "topology-agent-profile-modal",
    "topology-agent-roster",
    "cybersecurity-factory-view",
    "factory-swarm-pipeline",
    "factory-agent-roster",
    "run-selector",
    "approval-queue-list",
    "task-flow-grid",
    "factory-e2e-evidence-board"
  ];

  requiredElements.forEach((el) => {
    if (html.includes(`id="${el}"`) || html.includes(`id='${el}'`)) {
      findings.push(`Element checked: ${el}`);
    } else {
      errors.push(`Missing Element ID in HTML: ${el}`);
    }
  });

  // Verify no Tailwind CDN
  if (html.includes("cdn.tailwindcss.com")) {
    errors.push("Tailwind CDN script tag found in index.html! CDN tailwind is prohibited in production.");
  } else {
    findings.push("No Tailwind CDN used: OK");
  }

  // Verify no react root mounts or legacy entry points
  if (html.includes("/src/main.tsx")) {
    errors.push("Legacy entry point /src/main.tsx found in index.html");
  } else {
    findings.push("No /src/main.tsx entry point found: OK");
  }

  if (html.includes("react-hochster-root")) {
    errors.push("react-hochster-root container found in index.html");
  } else {
    findings.push("No react-hochster-root container found: OK");
  }

  writeReport(errors, findings);
}

function writeReport(errors: string[], findings: string[]) {
  const status = errors.length === 0 ? "PASS" : "FAIL";
  const report = {
    generated_at: new Date().toISOString(),
    status,
    errors,
    findings
  };

  const reportPath = path.resolve(__dirname, "../../artifacts/qa/full-page-swarm-audit-report.json");
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`Inventory Audit completed with status: ${status}`);
  if (errors.length > 0) {
    console.error("Errors found:", errors);
    process.exit(1);
  } else {
    console.log("All inventory checks passed!");
    process.exit(0);
  }
}

runAudit();
