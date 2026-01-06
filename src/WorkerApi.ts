/// Worker API that interacts with a Pyodide worker.

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

  constructor() {
    this.callbacks = {};
    this.id = 0;
    this.worker = new Worker(new URL("./pyodide-worker", import.meta.url), {
      type: "classic",
    });
    this.worker.onmessage = (event) => this.onMessage(event.data);
  }

  private invokeCallback(message: FinishedMessage) {
    const id = message.id;
    const onSuccess = this.callbacks[id];
    delete this.callbacks[id];
    onSuccess(message);
  }

  onStderr(message: StderrMessage) {
    console.error(message.stderr);
  }

  onStdout(message: StdoutMessage) {
    console.log(message.stdout);
  }

  async addFile(name: string, fileData: Uint8Array) {
    await this.sendMessageAwaitable({
      kind: "addFile",
      name,
      fileData,
    });
  }

  async removeFile(name: string) {
    await this.sendMessageAwaitable({
      kind: "removeFile",
      name,
    });
  }

  async fileContent(name: string): Promise<Uint8Array> {
    const message = await this.sendMessageAwaitable({
      kind: "fileContent",
      name,
    });

    if (message.error !== undefined || message.result === undefined)
      throw new Error(message.error);

    return message.result;
  }

  private onMessage(message: Message) {
    switch (message.kind) {
      case "finished":
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
    return new Promise((onSuccess) => {
      this.callbacks[this.id] = onSuccess;
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
}
