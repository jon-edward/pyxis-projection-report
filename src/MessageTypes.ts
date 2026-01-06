/// Shared message types between worker and main thread

export interface FinishedMessage {
  kind: "finished";
  id: number;
  error?: string;
  result?: any;
}

export interface AddFileMessage {
  kind: "addFile";
  id: number;
  name: string;
  fileData: Uint8Array;
}

export interface RemoveFileMessage {
  kind: "removeFile";
  id: number;
  name: string;
}

export interface FileContentMessage {
  kind: "fileContent";
  id: number;
  name: string;
}

export interface FileContentResult {
  kind: "finished";
  id: number;
  fileData?: Uint8Array;
  error?: string;
}

export interface StderrMessage {
  kind: "stderr";
  stderr: Uint8Array;
}

export interface StdoutMessage {
  kind: "stdout";
  stdout: Uint8Array;
}

export interface RunMessage {
  kind: "run";
  id: number;
  python: string;
  options?: {
    globals?: Record<string, any>;
    locals?: Record<string, any>;
  };
}

export type Message =
  | FinishedMessage
  | StderrMessage
  | StdoutMessage
  | AddFileMessage
  | RemoveFileMessage
  | RunMessage
  | FileContentMessage;
