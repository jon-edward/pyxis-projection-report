// Pyodide webworker script.

import type { Message, RunMessage } from "./MessageTypes";

// Define the global Pyodide type and loadPyodide function, imported pyodide
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js");
declare function loadPyodide(): Promise<any>;

function sendStdout(stdout: Uint8Array) {
  self.postMessage({ kind: "stdout", stdout });
}

function sendStderr(stderr: Uint8Array) {
  self.postMessage({ kind: "stderr", stderr });
}

async function initPyodide() {
  /**
   * Pyodide initialization handling dependencies.
   * Load the Pyodide module and initialize it. Returns a promise that
   * resolves to the Pyodide instance.
   */
  const pyodide = await loadPyodide();
  pyodide.setStdout({ batched: sendStdout });
  pyodide.setStderr({ batched: sendStderr });

  await pyodide.runPythonAsync(`
from pyodide.http import pyfetch
response = await pyfetch("/lib.zip")
await response.unpack_archive()
`);

  await pyodide.loadPackage("micropip");
  await pyodide.runPythonAsync(`
import micropip
with open("requirements.txt") as f:
  requirements = [req.strip() for req in f.readlines() if req.strip()]
for req in requirements:
  print(f"Installing {req}")
  await micropip.install(req)
  print(f"Installed {req}")
`);

  return pyodide;
}

const pyodidePromise = initPyodide();

async function onRun(message: RunMessage) {
  let result: any = null;
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
    result = await pyodide.runPythonAsync(python, pyOptions);
  } catch (error: any) {
    self.postMessage({ kind: "finished", error: error.message, id });
    return;
  }

  self.postMessage({ kind: "finished", result, id });
}

self.onmessage = async (event: MessageEvent<Message>) => {
  const { data } = event;

  switch (data.kind) {
    case "addFile": {
      const { name, fileData, id } = data;
      const pyodide = await pyodidePromise;
      pyodide.FS.writeFile(name, fileData);
      self.postMessage({ kind: "finished", id });
      break;
    }
    case "removeFile": {
      const { name, id } = data;
      const pyodide = await pyodidePromise;
      pyodide.FS.unlink(name);
      self.postMessage({ kind: "finished", id });
      break;
    }
    case "fileContent": {
      const { name, id } = data;
      const pyodide = await pyodidePromise;
      const fileData = pyodide.FS.readFile(name);
      self.postMessage({ kind: "finished", result: fileData, id });
      break;
    }
    case "run": {
      await onRun(data);
      break;
    }
  }
};
