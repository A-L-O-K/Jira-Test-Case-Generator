const API_URL = "http://127.0.0.1:5000/api/v1/test-cases/generate";
const CREATE_API_URL = "http://127.0.0.1:5000/api/v1/test-cases/create";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const apiUrl = message?.type === "generate-test-cases"
    ? API_URL
    : message?.type === "create-jira-test-cases"
      ? CREATE_API_URL
      : null;
  if (!apiUrl) return;

  fetch(apiUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message.payload)
  })
    .then(async response => {
      const body = await response.json().catch(() => null);
      sendResponse({
        ok: response.ok,
        status: response.status,
        body
      });
    })
    .catch(error => {
      sendResponse({
        ok: false,
        status: 0,
        error: error instanceof Error ? error.message : "The local backend could not be reached."
      });
    });

  return true;
});
