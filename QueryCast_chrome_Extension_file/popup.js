// Wait for the DOM to be fully loaded before running any script
document.addEventListener("DOMContentLoaded", () => {
  // Get the active tab in the current window
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const url = tabs[0]?.url || "";

    // If the tab is a YouTube video, auto-fill the input with its URL
    if (url.includes("youtube.com/watch")) {
      document.getElementById("videoUrl").value = url;
    }
  });

  // Attach event listener to the "Ask" button
  document.getElementById("askBtn").addEventListener("click", handleAsk);
});

// Function to handle the "Ask" button click
async function handleAsk() {
  // Get the values from the input fields
  const videoUrl = document.getElementById("videoUrl").value.trim();
  const question = document.getElementById("question").value.trim();
  const responseDiv = document.getElementById("response");

  // Show a loading message while waiting for the response
  responseDiv.textContent = "Thinking...";

  // Validate inputs
  if (!videoUrl || !question) {
    responseDiv.textContent = "Please enter both the video URL and a question.";
    return;
  }

  try {
    // Send a POST request to the Flask backend API with the video URL and question
    const res = await fetch("http://127.0.0.1:5000/api/askyou", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ videoUrl, question }), // Request payload
    });

    // Parse the response as JSON
    const data = await res.json();

    // Display the response from the backend if successful
    if (res.ok) {
      responseDiv.textContent = data.response;
    } else {
      // Show error message returned from the backend
      responseDiv.textContent = `Error: ${data.error || 'Unknown error occurred.'}`;
    }
  } catch (err) {
    // Handle fetch errors (e.g., server not running or network issues)
    console.error("Request failed:", err);
    responseDiv.textContent = "Could not reach backend. Make sure it’s running.";
  }
}
