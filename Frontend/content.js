(() => {
  const ROOT_ID = "jira-test-case-generator-root";
  const STORY_KEY_PATTERN = /^[A-Z][A-Z0-9_]*-\d+$/i;

  let root;
  let shadow;

  function getStoryKey() {
    const issueRouteMatch = location.pathname.match(
      /\/(?:browse|issues)\/([A-Z][A-Z0-9_]*-\d+)(?:\/|$)/i
    );
    const params = new URL(location.href).searchParams;
    const candidate = issueRouteMatch?.[1]
      ?? params.get("selectedIssue")
      ?? params.get("issueKey")
      ?? document.querySelector("[data-issue-key]")?.getAttribute("data-issue-key")
      ?? document.querySelector("#key-val")?.textContent?.trim();
    return candidate && STORY_KEY_PATTERN.test(candidate) ? candidate.toUpperCase() : null;
  }

  function getText(selectors) {
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      const text = element?.innerText?.trim() || element?.textContent?.trim();
      if (text) return text;
    }
    return "";
  }

  function isStoryPage() {
    const storyKey = getStoryKey();
    if (!storyKey) return false;

    const isAtlassian = location.hostname === "atlassian.net"
      || location.hostname.endsWith(".atlassian.net");
    const hasJiraMarkers = Boolean(document.querySelector(
      "#jira, #key-val, [data-testid*='issue.views.issue-base']"
    ));
    if (!isAtlassian && !hasJiraMarkers) return false;

    const issueType = getText([
      '[data-testid*="issue-type"]',
      "#type-val"
    ]);
    return !issueType || issueType.toLowerCase() === "story";
  }

  function getStoryDetails(storyKey) {
    const summary = getText([
      '[data-testid="issue.views.issue-base.foundation.summary.heading"]',
      "#summary-val",
      'h1[id="summary-val"]',
      "main h1"
    ]);
    const description = getText([
      '[data-testid="issue.views.field.rich-text.description"]',
      '[data-testid*="description"]',
      "#description-val",
      '[id*="description-val"]'
    ]);
    const status = getText([
      '[data-testid*="status"]',
      "#status-val"
    ]);
    const type = getText([
      '[data-testid*="issue-type"]',
      "#type-val"
    ]);

    return {
      key: storyKey,
      summary,
      description,
      ...(status ? { status } : {}),
      ...(type ? { type } : { type: "Story" })
    };
  }

  function addStyles() {
    const style = document.createElement("style");
    style.textContent = `
      :host { all: initial; color: #172b4d; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
      *, *::before, *::after { box-sizing: border-box; }
      .launcher {
        position: fixed; right: 24px; bottom: 24px; z-index: 2147483646;
        border: 0; border-radius: 6px; padding: 12px 18px; background: #0c66e4;
        color: white; font-size: 14px; font-weight: 600; cursor: pointer;
        box-shadow: 0 4px 12px #091e4240;
      }
      .launcher:hover, .primary:hover { background: #0055cc; }
      .backdrop {
        position: fixed; inset: 0; z-index: 2147483647; display: flex;
        justify-content: center; align-items: center; padding: 24px;
        background: #091e427a;
      }
      .dialog {
        display: flex; flex-direction: column; width: min(700px, 100%); max-height: min(820px, 90vh);
        overflow: hidden; border-radius: 8px; background: #fff;
        box-shadow: 0 8px 32px #091e4240;
      }
      header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid #dfe1e6; }
      h2 { margin: 0; font-size: 20px; line-height: 1.3; }
      .story-key { margin-top: 4px; color: #626f86; font-size: 13px; }
      .close {
        border: 0; background: transparent; color: #44546f; cursor: pointer;
        font-size: 24px; line-height: 1; padding: 4px 8px;
      }
      .content { overflow-y: auto; padding: 20px 24px; }
      label { display: block; margin-bottom: 8px; font-size: 14px; font-weight: 600; }
      textarea {
        display: block; width: 100%; min-height: 84px; resize: vertical;
        border: 1px solid #8590a2; border-radius: 4px; padding: 10px 12px;
        color: #172b4d; font: inherit; font-size: 14px;
      }
      textarea:focus { outline: 2px solid #0c66e4; outline-offset: 1px; }
      .submit-row { display: flex; justify-content: flex-end; margin-top: 12px; }
      button.primary, button.secondary {
        border: 0; border-radius: 4px; padding: 9px 16px;
        font: inherit; font-size: 14px; font-weight: 600; cursor: pointer;
      }
      .primary { background: #0c66e4; color: #fff; }
      .secondary { background: #f1f2f4; color: #172b4d; }
      .secondary:hover { background: #dcdfe4; }
      button:disabled { cursor: wait; opacity: .65; }
      .message { margin: 14px 0 0; color: #44546f; font-size: 14px; }
      .message.error { color: #ae2e24; }
      .message.success { color: #216e4e; }
      .case-list { display: grid; gap: 12px; margin-top: 20px; }
      .case {
        border: 1px solid #dfe1e6; border-radius: 6px; padding: 14px;
      }
      .case-heading { display: flex; gap: 10px; align-items: flex-start; }
      .case-heading input { flex: none; margin: 3px 0 0; accent-color: #0c66e4; }
      .case-title { font-size: 15px; font-weight: 600; }
      .case-id { display: block; margin-top: 3px; color: #626f86; font-size: 12px; }
      .case-detail { margin: 12px 0 0; font-size: 13px; line-height: 1.5; }
      .case-detail strong { display: block; margin-bottom: 3px; }
      .case-detail ul, .case-detail ol { margin: 4px 0 0; padding-left: 22px; }
      .actions { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 24px; border-top: 1px solid #dfe1e6; }
      [hidden] { display: none !important; }
      @media (max-width: 520px) {
        .backdrop { padding: 12px; }
        .dialog { max-height: 94vh; }
        header, .content { padding-left: 16px; padding-right: 16px; }
        .actions { padding: 12px 16px; }
      }
    `;
    shadow.append(style);
  }

  function closeDialog() {
    shadow.querySelector(".backdrop")?.remove();
  }

  function makeElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function renderTestCase(testCase, index) {
    const card = makeElement("article", "case");
    const heading = makeElement("div", "case-heading");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.setAttribute("aria-label", `Select ${testCase.title || `test case ${index + 1}`}`);
    checkbox.dataset.caseIndex = String(index);

    const headingText = document.createElement("div");
    headingText.append(makeElement("div", "case-title", testCase.title || `Test case ${index + 1}`));
    if (testCase.id) headingText.append(makeElement("span", "case-id", testCase.id));
    heading.append(checkbox, headingText);
    card.append(heading);

    if (Array.isArray(testCase.preconditions) && testCase.preconditions.length) {
      const detail = makeElement("div", "case-detail");
      detail.append(makeElement("strong", "", "Preconditions"));
      const list = document.createElement("ul");
      testCase.preconditions.forEach(item => list.append(makeElement("li", "", item)));
      detail.append(list);
      card.append(detail);
    }
    if (Array.isArray(testCase.steps) && testCase.steps.length) {
      const detail = makeElement("div", "case-detail");
      detail.append(makeElement("strong", "", "Steps"));
      const list = document.createElement("ol");
      testCase.steps.forEach(item => list.append(makeElement("li", "", item)));
      detail.append(list);
      card.append(detail);
    }
    if (testCase.expected_result) {
      const detail = makeElement("div", "case-detail");
      detail.append(
        makeElement("strong", "", "Expected result"),
        makeElement("span", "", testCase.expected_result)
      );
      card.append(detail);
    }
    return card;
  }

  function showDialog() {
    if (shadow.querySelector(".backdrop")) return;

    const storyKey = getStoryKey();
    if (!storyKey) return;
    let isCreating = false;

    const backdrop = makeElement("div", "backdrop");
    backdrop.addEventListener("click", event => {
      if (!isCreating && event.target === backdrop) closeDialog();
    });

    const dialog = makeElement("section", "dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-labelledby", "tcg-title");
    const header = document.createElement("header");
    const titleGroup = document.createElement("div");
    const title = makeElement("h2", "", "Generate test cases");
    title.id = "tcg-title";
    titleGroup.append(title, makeElement("div", "story-key", storyKey));
    const closeButton = makeElement("button", "close", "×");
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "Close");
    closeButton.addEventListener("click", () => {
      if (!isCreating) closeDialog();
    });
    header.append(titleGroup, closeButton);

    const content = makeElement("div", "content");
    const instructionsLabel = makeElement("label", "", "Additional instructions (optional)");
    instructionsLabel.htmlFor = "tcg-instructions";
    const instructions = document.createElement("textarea");
    instructions.id = "tcg-instructions";
    instructions.placeholder = "Add any guidance for generating test cases";
    content.append(instructionsLabel, instructions);

    const submitRow = makeElement("div", "submit-row");
    const submit = makeElement("button", "primary", "Submit");
    submit.type = "button";
    submitRow.append(submit);
    content.append(submitRow);

    const message = makeElement("p", "message");
    message.setAttribute("role", "status");
    content.append(message);
    const caseList = makeElement("div", "case-list");
    caseList.setAttribute("aria-label", "Generated test cases");
    content.append(caseList);

    const actions = makeElement("footer", "actions");
    actions.hidden = true;
    const cancel = makeElement("button", "secondary", "Cancel");
    cancel.type = "button";
    cancel.addEventListener("click", () => {
      if (!isCreating) closeDialog();
    });
    const create = makeElement("button", "primary", "Create in Jira");
    create.type = "button";
    actions.append(cancel, create);

    submit.addEventListener("click", async () => {
      submit.disabled = true;
      message.classList.remove("error");
      message.textContent = "Generating test cases…";
      caseList.replaceChildren();
      actions.hidden = true;

      const story = getStoryDetails(storyKey);
      if (!story.summary || !story.description) {
        message.classList.add("error");
        message.textContent = "Could not read the story summary and description from this Jira page.";
        submit.disabled = false;
        return;
      }

      const payload = {
        story_key: storyKey,
        story,
        instructions: instructions.value.trim()
      };

      try {
        const apiResponse = await chrome.runtime.sendMessage({
          type: "generate-test-cases",
          payload
        });
        const result = apiResponse?.body;
        if (!apiResponse?.ok) {
          throw new Error(
            result?.error
              || apiResponse?.error
              || (apiResponse?.status ? `The server returned HTTP ${apiResponse.status}.` : "The local backend could not be reached.")
          );
        }

        const testCases = result?.data?.test_cases;
        if (!Array.isArray(testCases)) {
          throw new Error("The server response did not contain a test_cases array.");
        }
        testCases.forEach((testCase, index) => caseList.append(renderTestCase(testCase, index)));
        message.textContent = testCases.length
          ? "Review and select the test cases you want to create."
          : "The server returned no test cases.";
        actions.hidden = false;

        create.onclick = async () => {
          const selectedCases = [...caseList.querySelectorAll('input[type="checkbox"]:checked')]
            .map(input => testCases[Number(input.dataset.caseIndex)])
            .filter(Boolean);
          if (!selectedCases.length) {
            message.classList.add("error");
            message.textContent = "Select at least one test case to create in Jira.";
            return;
          }

          create.disabled = true;
          isCreating = true;
          dialog.setAttribute("aria-busy", "true");
          submit.disabled = true;
          cancel.disabled = true;
          closeButton.disabled = true;
          caseList.querySelectorAll('input[type="checkbox"]').forEach(input => {
            input.disabled = true;
          });
          message.classList.remove("error", "success");
          message.textContent = `Creating ${selectedCases.length} Jira task${selectedCases.length === 1 ? "" : "s"}. Please wait…`;
          try {
            const createResponse = await chrome.runtime.sendMessage({
              type: "create-jira-test-cases",
              payload: {
                story_key: storyKey,
                test_case_ids: selectedCases.map(testCase => testCase.id)
              }
            });
            const createResult = createResponse?.body;
            const created = Array.isArray(createResult?.data?.created)
              ? createResult.data.created
              : [];

            const allCreatedAndLinked = createResponse?.ok
              && created.length === selectedCases.length
              && selectedCases.every(testCase =>
                created.some(item =>
                  item.test_case_id === testCase.id
                  && typeof item.key === "string"
                  && item.linked === true
                )
              );
            if (!allCreatedAndLinked) {
              const createdKeys = created.map(item => item.key).join(", ");
              const partialSuccess = createdKeys
                ? ` Jira created ${createdKeys}; linked: ${created.filter(item => item.linked).map(item => item.key).join(", ") || "none"}.`
                : "";
              throw new Error(
                `${createResult?.error || createResponse?.error || "Jira could not create all selected test cases."}${partialSuccess}`
              );
            }

            isCreating = false;
            dialog.removeAttribute("aria-busy");
            closeButton.disabled = false;
            cancel.disabled = false;
            instructionsLabel.hidden = true;
            instructions.hidden = true;
            submitRow.hidden = true;
            caseList.hidden = true;
            create.hidden = true;
            cancel.textContent = "Close";
            message.classList.add("success");
            message.textContent = `Successfully created ${created.length} test case${created.length === 1 ? "" : "s"} and linked ${created.length === 1 ? "it" : "them"} to ${storyKey}.`;
          } catch (error) {
            isCreating = false;
            dialog.removeAttribute("aria-busy");
            submit.disabled = false;
            cancel.disabled = false;
            closeButton.disabled = false;
            instructionsLabel.hidden = true;
            instructions.hidden = true;
            submitRow.hidden = true;
            caseList.hidden = true;
            create.hidden = true;
            cancel.textContent = "Close";
            message.classList.remove("success");
            message.classList.add("error");
            message.textContent = error instanceof Error
              ? `Unable to create test cases in Jira: ${error.message}`
              : "Unable to create test cases in Jira because of an unexpected error.";
          }
        };
      } catch (error) {
        message.classList.add("error");
        message.textContent = error instanceof Error
          ? `Unable to generate test cases: ${error.message}`
          : "Unable to generate test cases because of an unexpected error.";
        actions.hidden = true;
      } finally {
        submit.disabled = false;
      }
    });

    dialog.append(header, content, actions);
    backdrop.append(dialog);
    shadow.append(backdrop);
    instructions.focus();
  }

  function syncVisibility() {
    if (!isStoryPage()) {
      root?.remove();
      root = undefined;
      shadow = undefined;
      return;
    }
    if (root?.isConnected) return;

    root = document.createElement("div");
    root.id = ROOT_ID;
    shadow = root.attachShadow({ mode: "closed" });
    addStyles();
    const launcher = makeElement("button", "launcher", "Generate test cases");
    launcher.type = "button";
    launcher.addEventListener("click", showDialog);
    shadow.append(launcher);
    document.documentElement.append(root);
  }

  syncVisibility();
  window.setInterval(() => {
    syncVisibility();
  }, 500);
})();
