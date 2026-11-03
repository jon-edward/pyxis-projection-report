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

// Pyodide passes each line of output as a string; bytes are accepted too.
export interface StderrMessage {
  kind: "stderr";
  stderr: string | Uint8Array;
}

export interface StdoutMessage {
  kind: "stdout";
  stdout: string | Uint8Array;
}

/** Progress reported by the Python report code (see py/projection_report/progress.py). */
export interface ProgressUpdate {
  stage: string;
  done: number;
  total: number;
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
