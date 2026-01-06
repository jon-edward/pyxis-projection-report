import { For, createSignal } from "solid-js";
import {
  createForm,
  valiForm,
  remove,
  insert,
  FormStore,
} from "@modular-forms/solid";
import * as v from "valibot";
import WorkerApi from "./WorkerApi";

const ReportConfigSchema = v.object({
  onlyCritical: v.boolean(),
  includeUnordered: v.boolean(),
  includeMinZero: v.boolean(),
  criticalThreshold: v.number(),
  maxDays: v.number(),
  devices: v.array(v.pipe(v.string(), v.trim())),
  exclude: v.array(v.pipe(v.string(), v.trim())),
  usageFile: v.file(),
  inventoryFile: v.file(),
});

type ReportConfig = v.InferInput<typeof ReportConfigSchema>;

// Reusable Components
interface CheckboxFieldProps {
  name: "onlyCritical" | "includeUnordered" | "includeMinZero";
  label: string;
  Field: any;
}

function CheckboxField(props: CheckboxFieldProps) {
  const { name, label, Field } = props;
  const id = name.toLowerCase().replace(/([A-Z])/g, "-$1");

  return (
    <div style={{ "margin-bottom": "1rem" }}>
      <Field name={name} type="boolean">
        {(field: any, inputProps: any) => (
          <div
            style={{ display: "flex", "align-items": "center", gap: "0.5rem" }}
          >
            <input
              type="checkbox"
              id={id}
              {...inputProps}
              checked={field.value}
            />
            <label for={id}>{label}</label>
          </div>
        )}
      </Field>
    </div>
  );
}

interface NumberFieldProps {
  name: "criticalThreshold" | "maxDays";
  label: string;
  Field: any;
}

function NumberField(props: NumberFieldProps) {
  const { name, label, Field } = props;

  return (
    <div style={{ "margin-bottom": "1rem" }}>
      <Field name={name} type="number">
        {(field: any, inputProps: any) => (
          <div style={{ display: "flex", "flex-direction": "column" }}>
            <label for={name} style={{ "font-weight": "bold" }}>
              {label}
            </label>
            <input
              type="number"
              id={name}
              {...inputProps}
              value={field.value ?? 0}
              style={{
                display: "block",
                padding: "0.5rem",
                "margin-top": "0.25rem",
                border: "1px solid #ccc",
                "border-radius": "4px",
              }}
            />
          </div>
        )}
      </Field>
    </div>
  );
}

interface FileFieldProps {
  name: "usageFile" | "inventoryFile";
  label: string;
  form: FormStore<ReportConfig, undefined>;
  errorMessage: string;
  Field: any;
}

function isExcelFile(file: File) {
  switch (file.type) {
    case "application/vnd.ms-excel (official)":
    case "application/msexcel":
    case "application/x-msexcel":
    case "application/x-ms-excel":
    case "application/x-excel":
    case "application/x-dos_ms_excel":
    case "application/xls":
    case "application/x-xls":
    case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
    case "application/vnd.ms-excel":
      return true;
    default:
      return false;
  }
}

function FileField(props: FileFieldProps) {
  const { name, label, Field, form } = props;
  return (
    <div style={{ "margin-bottom": "1rem" }}>
      <Field name={name} type="file">
        {(field: any, inputProps: any) => (
          <div style={{ display: "flex", "flex-direction": "column" }}>
            <label for={name} style={{ "font-weight": "bold" }}>
              {label}
            </label>
            <input
              style={{
                display: "block",
                padding: "0.5rem",
                "margin-top": "0.25rem",
                border: "1px solid #ccc",
                "border-radius": "4px",
              }}
              type="file"
              id={name}
              {...inputProps}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file && isExcelFile(file)) {
                  const fileSignal = form.internal.fields[props.name]?.value;
                  if (fileSignal) {
                    fileSignal.set(file);
                  }
                }
              }}
            />
            <div style={{ "margin-top": "0.5rem" }}>
              {field.error && (
                <span style={{ color: "red" }}>{props.errorMessage}</span>
              )}
            </div>
          </div>
        )}
      </Field>
    </div>
  );
}

interface DynamicListFieldProps {
  name: "devices" | "exclude";
  label: string;
  placeholder: string;
  form: FormStore<ReportConfig, undefined>;
  Field: any;
  FieldArray: any;
}

function DynamicListField(props: DynamicListFieldProps) {
  const { name, label, placeholder, form, Field, FieldArray } = props;

  return (
    <div style={{ "margin-bottom": "1.5rem" }}>
      <FieldArray name={name}>
        {(fieldArray: any) => (
          <div>
            <div style={{ "margin-bottom": "0.5rem" }}>
              <label style={{ "font-weight": "bold" }}>{label}</label>
            </div>
            <For each={fieldArray.items.slice(0, -1)}>
              {(item: any, index: () => number) => (
                <Field name={`${name}.${index()}`}>
                  {(field: any, inputProps: any) => (
                    <div style={{ "margin-bottom": "0.5rem" }}>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <input
                          {...inputProps}
                          value={field.value || ""}
                          placeholder={placeholder}
                          style={{
                            flex: 1,
                            padding: "0.5rem",
                            border: field.error
                              ? "1px solid red"
                              : "1px solid #ccc",
                            "border-radius": "4px",
                          }}
                        />
                        <button
                          type="button"
                          onClick={() => remove(form, name, { at: index() })}
                          style={{
                            padding: "0.5rem 1rem",
                            background: "#dc3545",
                            color: "white",
                            border: "none",
                            "border-radius": "4px",
                            cursor: "pointer",
                          }}
                        >
                          Remove
                        </button>
                      </div>
                      {field.error && (
                        <div
                          style={{
                            color: "red",
                            "font-size": "0.875rem",
                            "margin-top": "0.25rem",
                          }}
                        >
                          {field.error}
                        </div>
                      )}
                    </div>
                  )}
                </Field>
              )}
            </For>

            <Field name={`${name}.${fieldArray.items.length - 1}`}>
              {(field: any, inputProps: any) => (
                <div style={{ "margin-bottom": "0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <input
                      {...inputProps}
                      value={field.value || ""}
                      placeholder={placeholder}
                      style={{
                        flex: 1,
                        padding: "0.5rem",
                        border: field.error
                          ? "1px solid red"
                          : "1px solid #ccc",
                        "border-radius": "4px",
                      }}
                    />
                  </div>
                  {field.error && (
                    <div
                      style={{
                        color: "red",
                        "font-size": "0.875rem",
                        "margin-top": "0.25rem",
                      }}
                    >
                      {field.error}
                    </div>
                  )}
                </div>
              )}
            </Field>

            <div>
              <button
                type="button"
                onClick={() => insert(form, name, { value: "" })}
                style={{
                  padding: "0.5rem 1rem",
                  background: "#28a745",
                  color: "white",
                  border: "none",
                  "border-radius": "4px",
                  cursor: "pointer",
                }}
              >
                + Add device
              </button>
            </div>
          </div>
        )}
      </FieldArray>
    </div>
  );
}

// Main App Component
export default function App() {
  const [form, { Form, Field, FieldArray }] = createForm<ReportConfig>({
    validate: valiForm(ReportConfigSchema),
    initialValues: {
      onlyCritical: true,
      includeUnordered: false,
      includeMinZero: false,
      criticalThreshold: 3,
      maxDays: 5,
      devices: [""],
      exclude: [""],
    },
  });

  const [isLoading, setIsLoading] = createSignal(false);
  const [errorMessage, setError] = createSignal("");
  const worker = new WorkerApi();

  const handleSubmit = async (result: ReportConfig) => {
    setIsLoading(true);
    try {
      const inventory = await result.inventoryFile.arrayBuffer();
      const usage = await result.usageFile.arrayBuffer();

      await worker.runPython(
        `import os; os.makedirs("reports", exist_ok=True)`
      );

      await worker.addFile("reports/Inventory.xlsx", new Uint8Array(inventory));
      await worker.addFile("reports/Usage.xlsx", new Uint8Array(usage));

      const pyResult = {
        only_critical: result.onlyCritical,
        include_unordered: result.includeUnordered,
        include_min_zero: result.includeMinZero,
        critical_threshold: result.criticalThreshold,
        max_days: result.maxDays,
        devices: result.devices.filter((d) => d.length > 0),
        exclude: result.exclude.filter((d) => d.length > 0),
      };

      const report = await worker.runPython(
        `
import json
from projection_report.config import ReportConfig
from projection_report.report import create_report

config = ReportConfig(**json.loads(config_string))
create_report(config)
`,
        { locals: { config_string: JSON.stringify(pyResult) } }
      );

      if (report.error) {
        console.error(report.error);
        throw new Error("Error running Python code");
      }

      const fileData: Uint8Array = await worker.fileContent(
        "reports/projection_report.pdf"
      );

      await worker.removeFile("reports/Inventory.xlsx");
      await worker.removeFile("reports/Usage.xlsx");
      await worker.removeFile("reports/projection_report.pdf");

      const blob = new Blob([new Uint8Array(fileData)], {
        type: "application/pdf",
      });

      const url = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;

      link.download = "projection_report.pdf";
      link.style.display = "none";

      document.body.appendChild(link);
      link.click();

      setTimeout(() => {
        URL.revokeObjectURL(url);
        document.body.removeChild(link);
      }, 0);
    } catch (error) {
      setError("Error running Python code, check console for details.");
    }
    setIsLoading(false);
  };

  return (
    <div style={{ padding: "2rem", "max-width": "600px", margin: "0 auto" }}>
      <h1>Pyxis Inventory Report</h1>
      <h2>Report Parameters</h2>

      <div>
        <Form onSubmit={handleSubmit}>
          <CheckboxField
            name="onlyCritical"
            label="Only include critical items"
            Field={Field}
          />

          <CheckboxField
            name="includeUnordered"
            label="Include unordered items"
            Field={Field}
          />

          <CheckboxField
            name="includeMinZero"
            label="Include items with a min of 0"
            Field={Field}
          />

          <NumberField
            name="criticalThreshold"
            label="Critical threshold in days"
            Field={Field}
          />

          <NumberField name="maxDays" label="Max days" Field={Field} />

          <DynamicListField
            name="devices"
            label="Include devices"
            placeholder="Device name (eg. EMER)"
            form={form}
            Field={Field}
            FieldArray={FieldArray}
          />

          <DynamicListField
            name="exclude"
            label="Exclude devices"
            placeholder="Device name (eg. EMER)"
            form={form}
            Field={Field}
            FieldArray={FieldArray}
          />

          <FileField
            name="usageFile"
            label="Usage File"
            Field={Field}
            errorMessage="Please provide a Pyxis usage Excel file"
            form={form}
          />

          <FileField
            name="inventoryFile"
            label="Inventory File"
            Field={Field}
            errorMessage="Please provide a Pyxis inventory Excel file"
            form={form}
          />

          <button
            type="submit"
            style={{
              padding: "0.75rem 1.5rem",
              background: isLoading() ? "#ccc" : "#0066cc",
              color: "white",
              border: "none",
              "border-radius": "4px",
              cursor: isLoading() ? "not-allowed" : "pointer",
              "font-size": "1rem",
              width: "100%",
            }}
            disabled={isLoading()}
          >
            Run Report
          </button>

          {errorMessage() && <p style={{ color: "red" }}>{errorMessage()}</p>}
        </Form>
      </div>
    </div>
  );
}
