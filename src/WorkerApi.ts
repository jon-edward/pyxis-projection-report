import type {
  FinishedMessage,
  Message,
  StderrMessage,
  StdoutMessage,
} from "./MessageTypes";

/**
 * Defines internal behavior for interacting with a Pyodide worker through an awaitable API.
 */
export default class WorkerApi {
  private callbacks: Record<number, (message: FinishedMessage) => void>;
  private worker: Worker;
  private id: number;
  private isInitialized: boolean;
  private initializationPromise: Promise<void> | null;

  constructor() {
    this.callbacks = {};
    this.id = 0;
    this.isInitialized = false;
    this.initializationPromise = null;
    this.worker = new Worker(new URL("./pyodide-worker", import.meta.url), {
      type: "classic",
    });
    this.worker.onmessage = (event) => this.onMessage(event.data);
    this.worker.onerror = (error) => {
      console.error("Worker error:", error);
    };
  }

  private invokeCallback(message: FinishedMessage) {
    const id = message.id;
    const onSuccess = this.callbacks[id];
    if (onSuccess) {
      delete this.callbacks[id];
      onSuccess(message);
    }
  }

  onStderr(message: StderrMessage) {
    console.error("Python stderr:", message.stderr);
  }

  onStdout(message: StdoutMessage) {
    console.log("Python stdout:", message.stdout);
  }

  /**
   * Wait for the worker to be initialized before running commands
   */
  async waitForInitialization(): Promise<void> {
    if (this.isInitialized) return;

    if (!this.initializationPromise) {
      this.initializationPromise = new Promise((resolve) => {
        // Wait for first successful operation to consider initialized
        const checkInit = setInterval(() => {
          if (this.isInitialized) {
            clearInterval(checkInit);
            resolve();
          }
        }, 100);
      });
    }

    return this.initializationPromise;
  }

  async addFile(name: string, fileData: Uint8Array): Promise<void> {
    const result = await this.sendMessageAwaitable({
      kind: "addFile",
      name,
      fileData,
    });

    if (result.error) {
      throw new Error(`Failed to add file ${name}: ${result.error}`);
    }
  }

  async removeFile(name: string): Promise<void> {
    const result = await this.sendMessageAwaitable({
      kind: "removeFile",
      name,
    });

    if (result.error) {
      throw new Error(`Failed to remove file ${name}: ${result.error}`);
    }
  }

  async fileContent(name: string): Promise<Uint8Array> {
    const message = await this.sendMessageAwaitable({
      kind: "fileContent",
      name,
    });

    if (message.error !== undefined) {
      throw new Error(`Failed to read file ${name}: ${message.error}`);
    }

    if (message.result === undefined) {
      throw new Error(`File ${name} not found or empty`);
    }

    return message.result;
  }

  private onMessage(message: Message) {
    switch (message.kind) {
      case "finished":
        this.isInitialized = true;
        this.invokeCallback(message);
        break;
      case "stderr":
        this.onStderr(message);
        break;
      case "stdout":
        this.onStdout(message);
        break;
    }
  }

  private async sendMessageAwaitable(data: any): Promise<FinishedMessage> {
    this.id = (this.id + 1) % Number.MAX_SAFE_INTEGER;
    return new Promise((onSuccess, reject) => {
      const timeoutId = setTimeout(() => {
        delete this.callbacks[this.id];
        reject(new Error("Worker operation timed out after 10 minutes"));
      }, 600000); // 10 minute timeout

      this.callbacks[this.id] = (message: FinishedMessage) => {
        clearTimeout(timeoutId);
        onSuccess(message);
      };

      this.worker.postMessage({
        id: this.id,
        ...data,
      });
    });
  }

  async runPython(
    python: string,
    options: Record<string, any> = {}
  ): Promise<FinishedMessage> {
    return await this.sendMessageAwaitable({
      kind: "run",
      python,
      options,
    });
  }

  /**
   * Terminate the worker and cleanup resources
   */
  terminate(): void {
    this.worker.terminate();
    this.callbacks = {};
  }
}
