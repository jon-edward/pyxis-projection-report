// Pyodide webworker script.

import type { Message, RunMessage } from "./MessageTypes";

// Import Pyodide from CDN
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js");
declare function loadPyodide(): Promise<any>;

function sendStdout(stdout: Uint8Array) {
  self.postMessage({ kind: "stdout", stdout });
}

function sendStderr(stderr: Uint8Array) {
  self.postMessage({ kind: "stderr", stderr });
}

function sendProgress(message: string) {
  console.log(`[Pyodide] ${message}`);
}

async function initPyodide() {
  try {
    sendProgress("Loading Pyodide...");
    const pyodide = await loadPyodide();

    pyodide.setStdout({ batched: sendStdout });
    pyodide.setStderr({ batched: sendStderr });

    sendProgress("Unpacking Python library...");
    await pyodide.runPythonAsync(`
from pyodide.http import pyfetch
import sys
response = await pyfetch("/lib.zip")
await response.unpack_archive()
`);

    sendProgress("Loading package manager...");
    await pyodide.loadPackage("micropip");

    sendProgress("Installing Python dependencies...");
    await pyodide.runPythonAsync(`
import micropip
import sys

try:
    with open("requirements.txt") as f:
        requirements = [req.strip() for req in f.readlines() if req.strip() and not req.startswith('#')]
    for req in requirements:
        await micropip.install(req)
except Exception as e:
    print(f"Error installing dependencies: {e}", file=sys.stderr)
    raise
`);

    sendProgress("Pyodide initialized successfully");
    return pyodide;
  } catch (error: any) {
    sendProgress(`Failed to initialize Pyodide: ${error.message}`);
    throw error;
  }
}

const pyodidePromise = initPyodide();

async function onRun(message: RunMessage) {
  const { python, options, id } = message;

  try {
    const pyodide = await pyodidePromise;
    const pyOptions: Record<string, any> = {};

    if (options?.globals) {
      pyOptions.globals = pyodide.toPy({
        ...options.globals,
      });
    }

    if (options?.locals) {
      pyOptions.locals = pyodide.toPy({
        ...options.locals,
      });
    }

    const result = await pyodide.runPythonAsync(python, pyOptions);
    self.postMessage({ kind: "finished", result, id });
  } catch (error: any) {
    console.error("Python execution error:", error);
    self.postMessage({
      kind: "finished",
      error: error.message || "Unknown Python execution error",
      id,
    });
  }
}

self.onmessage = async (event: MessageEvent<Message>) => {
  const { data } = event;

  try {
    switch (data.kind) {
      case "addFile": {
        const { name, fileData, id } = data;
        const pyodide = await pyodidePromise;

        // Ensure directory exists
        const dirPath = name.substring(0, name.lastIndexOf("/"));
        if (dirPath) {
          pyodide.FS.mkdirTree(dirPath);
        }

        pyodide.FS.writeFile(name, fileData);
        self.postMessage({ kind: "finished", id });
        break;
      }
      case "removeFile": {
        const { name, id } = data;
        const pyodide = await pyodidePromise;

        try {
          pyodide.FS.unlink(name);
          self.postMessage({ kind: "finished", id });
        } catch (error: any) {
          // File might not exist, that's okay
          self.postMessage({ kind: "finished", id });
        }
        break;
      }
      case "fileContent": {
        const { name, id } = data;
        const pyodide = await pyodidePromise;

        try {
          const fileData = pyodide.FS.readFile(name);
          self.postMessage({ kind: "finished", result: fileData, id });
        } catch (error: any) {
          self.postMessage({
            kind: "finished",
            error: `File not found: ${name}`,
            id,
          });
        }
        break;
      }
      case "run": {
        await onRun(data);
        break;
      }
    }
  } catch (error: any) {
    console.error("Worker error:", error);
    if ("id" in data) {
      self.postMessage({
        kind: "finished",
        error: error.message || "Unknown worker error",
        id: data.id,
      });
    }
  }
};

// Handle unhandled errors in the worker
self.onerror = (error) => {
  console.error("Unhandled worker error:", error);
  return false;
};
