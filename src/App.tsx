import { For, createSignal, Show } from "solid-js";
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
  description?: string;
  Field: any;
}

function CheckboxField(props: CheckboxFieldProps) {
  const { name, label, description, Field } = props;
  const id = name.toLowerCase().replace(/([A-Z])/g, "-$1");

  return (
    <div style={{ "margin-bottom": "1rem" }}>
      <Field name={name} type="boolean">
        {(field: any, inputProps: any) => (
          <div>
            <div
              style={{
                display: "flex",
                "align-items": "center",
                gap: "0.5rem",
              }}
            >
              <input
                type="checkbox"
                id={id}
                {...inputProps}
                checked={field.value}
                style={{
                  cursor: "pointer",
                  width: "18px",
                  height: "18px",
                }}
              />
              <label
                for={id}
                style={{
                  cursor: "pointer",
                  "font-weight": "500",
                  color: "#1e293b",
                }}
              >
                {label}
              </label>
            </div>
            {description && (
              <p
                style={{
                  "font-size": "0.875rem",
                  color: "#64748b",
                  "margin-top": "0.25rem",
                  "margin-left": "1.625rem",
                }}
              >
                {description}
              </p>
            )}
          </div>
        )}
      </Field>
    </div>
  );
}

interface NumberFieldProps {
  name: "criticalThreshold" | "maxDays";
  label: string;
  description?: string;
  Field: any;
}

function NumberField(props: NumberFieldProps) {
  const { name, label, description, Field } = props;

  return (
    <div style={{ "margin-bottom": "1rem" }}>
      <Field name={name} type="number">
        {(field: any, inputProps: any) => (
          <div style={{ display: "flex", "flex-direction": "column" }}>
            <label
              for={name}
              style={{
                "font-weight": "600",
                color: "#1e293b",
                "margin-bottom": "0.25rem",
              }}
            >
              {label}
            </label>
            {description && (
              <p
                style={{
                  "font-size": "0.875rem",
                  color: "#64748b",
                  "margin-bottom": "0.5rem",
                }}
              >
                {description}
              </p>
            )}
            <input
              type="number"
              id={name}
              {...inputProps}
              value={field.value ?? 0}
              style={{
                display: "block",
                padding: "0.625rem",
                border: "2px solid #e2e8f0",
                "border-radius": "8px",
                "font-size": "1rem",
                transition: "all 0.2s",
                outline: "none",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#3b82f6")}
              onBlur={(e) => (e.target.style.borderColor = "#e2e8f0")}
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
  const validTypes = [
    "application/vnd.ms-excel",
    "application/msexcel",
    "application/x-msexcel",
    "application/x-ms-excel",
    "application/x-excel",
    "application/x-dos_ms_excel",
    "application/xls",
    "application/x-xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ];
  return (
    validTypes.includes(file.type) ||
    file.name.endsWith(".xlsx") ||
    file.name.endsWith(".xls")
  );
}

function FileField(props: FileFieldProps) {
  const { name, label, Field, form } = props;
  const [selectedFile, setSelectedFile] = createSignal<File | null>(null);

  return (
    <div style={{ "margin-bottom": "1rem" }}>
      <Field name={name} type="file">
        {(field: any, inputProps: any) => (
          <div style={{ display: "flex", "flex-direction": "column" }}>
            <label
              for={name}
              style={{
                "font-weight": "600",
                color: "#1e293b",
                "margin-bottom": "0.5rem",
              }}
            >
              {label}
            </label>
            <input
              style={{
                display: "block",
                padding: "0.625rem",
                border: "2px solid #e2e8f0",
                "border-radius": "8px",
                "background-color": "#f8fafc",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              type="file"
              id={name}
              accept=".xlsx,.xls"
              {...inputProps}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file && isExcelFile(file)) {
                  setSelectedFile(file);
                  const fileSignal = form.internal.fields[props.name]?.value;
                  if (fileSignal) {
                    fileSignal.set(file);
                  }
                } else if (file) {
                  alert("Please select a valid Excel file (.xlsx or .xls)");
                  event.target.value = "";
                }
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.borderColor = "#cbd5e1")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.borderColor = "#e2e8f0")
              }
            />
            <Show when={selectedFile()}>
              <div
                style={{
                  "margin-top": "0.5rem",
                  padding: "0.5rem",
                  "background-color": "#f0f9ff",
                  border: "1px solid #bae6fd",
                  "border-radius": "6px",
                  "font-size": "0.875rem",
                  color: "#0c4a6e",
                }}
              >
                ✓ Selected: {selectedFile()!.name} (
                {(selectedFile()!.size / 1024).toFixed(1)} KB)
              </div>
            </Show>
            {field.error && (
              <div style={{ "margin-top": "0.5rem" }}>
                <span style={{ color: "#dc2626", "font-size": "0.875rem" }}>
                  {props.errorMessage}
                </span>
              </div>
            )}
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
  description?: string;
  form: FormStore<ReportConfig, undefined>;
  Field: any;
  FieldArray: any;
}

function DynamicListField(props: DynamicListFieldProps) {
  const { name, label, placeholder, description, form, Field, FieldArray } =
    props;

  return (
    <div style={{ "margin-bottom": "1.5rem" }}>
      <FieldArray name={name}>
        {(fieldArray: any) => (
          <div>
            <div style={{ "margin-bottom": "0.75rem" }}>
              <label style={{ "font-weight": "600", color: "#1e293b" }}>
                {label}
              </label>
              {description && (
                <p
                  style={{
                    "font-size": "0.875rem",
                    color: "#64748b",
                    "margin-top": "0.25rem",
                  }}
                >
                  {description}
                </p>
              )}
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
                            padding: "0.625rem",
                            border: field.error
                              ? "2px solid #dc2626"
                              : "2px solid #e2e8f0",
                            "border-radius": "8px",
                            "font-size": "1rem",
                            transition: "all 0.2s",
                            outline: "none",
                          }}
                          onFocus={(e) =>
                            !field.error &&
                            (e.target.style.borderColor = "#3b82f6")
                          }
                          onBlur={(e) =>
                            !field.error &&
                            (e.target.style.borderColor = "#e2e8f0")
                          }
                        />
                        <button
                          type="button"
                          onClick={() => remove(form, name, { at: index() })}
                          style={{
                            padding: "0.625rem 1rem",
                            background: "#dc2626",
                            color: "white",
                            border: "none",
                            "border-radius": "8px",
                            cursor: "pointer",
                            "font-weight": "500",
                            transition: "all 0.2s",
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = "#b91c1c")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "#dc2626")
                          }
                        >
                          Remove
                        </button>
                      </div>
                      {field.error && (
                        <div
                          style={{
                            color: "#dc2626",
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
                <div style={{ "margin-bottom": "0.75rem" }}>
                  <input
                    {...inputProps}
                    value={field.value || ""}
                    placeholder={placeholder}
                    style={{
                      width: "100%",
                      padding: "0.625rem",
                      border: field.error
                        ? "2px solid #dc2626"
                        : "2px solid #e2e8f0",
                      "border-radius": "8px",
                      "font-size": "1rem",
                      transition: "all 0.2s",
                      outline: "none",
                      "box-sizing": "border-box",
                    }}
                    onFocus={(e) =>
                      !field.error && (e.target.style.borderColor = "#3b82f6")
                    }
                    onBlur={(e) =>
                      !field.error && (e.target.style.borderColor = "#e2e8f0")
                    }
                  />
                  {field.error && (
                    <div
                      style={{
                        color: "#dc2626",
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

            <button
              type="button"
              onClick={() => insert(form, name, { value: "" })}
              style={{
                padding: "0.625rem 1rem",
                background: "#10b981",
                color: "white",
                border: "none",
                "border-radius": "8px",
                cursor: "pointer",
                "font-weight": "500",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#059669";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "#10b981";
              }}
            >
              + Add {name === "devices" ? "Device" : "Exclusion"}
            </button>
          </div>
        )}
      </FieldArray>
    </div>
  );
}

// Section wrapper component
function Section(props: {
  title: string;
  description?: string;
  children: any;
}) {
  return (
    <div
      style={{
        "margin-bottom": "2rem",
        padding: "1.5rem",
        background: "white",
        border: "1px solid #e2e8f0",
        "border-radius": "12px",
        "box-shadow": "0 1px 3px rgba(0, 0, 0, 0.05)",
      }}
    >
      <h3
        style={{
          "font-size": "1.125rem",
          "font-weight": "700",
          color: "#0f172a",
          "margin-bottom": "0.5rem",
        }}
      >
        {props.title}
      </h3>
      {props.description && (
        <p
          style={{
            "font-size": "0.875rem",
            color: "#64748b",
            "margin-bottom": "1.5rem",
          }}
        >
          {props.description}
        </p>
      )}
      {props.children}
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
  const [loadingStatus, setLoadingStatus] = createSignal("");
  const [errorMessage, setError] = createSignal("");
  const [successMessage, setSuccess] = createSignal("");
  const worker = new WorkerApi();

  const handleSubmit = async (result: ReportConfig) => {
    setIsLoading(true);
    setError("");
    setSuccess("");

    try {
      setLoadingStatus("Reading files...");
      const inventory = await result.inventoryFile.arrayBuffer();
      const usage = await result.usageFile.arrayBuffer();

      setLoadingStatus("Preparing Python environment...");
      await worker.runPython(
        `import os; os.makedirs("reports", exist_ok=True)`
      );

      setLoadingStatus("Uploading data files...");
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

      setLoadingStatus("Generating report...");
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
        throw new Error(report.error || "Error running Python code");
      }

      setLoadingStatus("Downloading report...");
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

      setSuccess(
        "Report generated successfully! Your download should begin shortly."
      );
    } catch (error: any) {
      console.error(error);
      setError(
        error.message ||
          "Error generating report. Please check your input files and try again."
      );
    }

    setIsLoading(false);
    setLoadingStatus("");
  };

  return (
    <div
      style={{
        "min-height": "100vh",
        background: "linear-gradient(to bottom right, #f8fafc, #e2e8f0)",
        padding: "2rem",
      }}
    >
      <div
        style={{
          "max-width": "800px",
          margin: "0 auto",
        }}
      >
        {/* Header */}
        <div
          style={{
            "margin-bottom": "2rem",
            padding: "2rem",
            background: "white",
            "border-radius": "12px",
            "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.05)",
            border: "1px solid #e2e8f0",
          }}
        >
          <h1
            style={{
              "font-size": "2rem",
              "font-weight": "800",
              color: "#0f172a",
              "margin-bottom": "0.5rem",
            }}
          >
            Pyxis Inventory Report Generator
          </h1>
          <p
            style={{
              color: "#64748b",
              "font-size": "1rem",
            }}
          >
            Configure and generate your inventory projection reports
          </p>
        </div>

        {/* Success Message */}
        <Show when={successMessage()}>
          <div
            style={{
              "margin-bottom": "1.5rem",
              padding: "1rem",
              background: "#dcfce7",
              border: "1px solid #86efac",
              "border-radius": "8px",
              color: "#166534",
              display: "flex",
              "align-items": "center",
              gap: "0.5rem",
            }}
          >
            <span style={{ "font-size": "1.25rem" }}>✓</span>
            <span>{successMessage()}</span>
          </div>
        </Show>

        {/* Error Message */}
        <Show when={errorMessage()}>
          <div
            style={{
              "margin-bottom": "1.5rem",
              padding: "1rem",
              background: "#fee2e2",
              border: "1px solid #fca5a5",
              "border-radius": "8px",
              color: "#991b1b",
              display: "flex",
              "align-items": "center",
              gap: "0.5rem",
            }}
          >
            <span style={{ "font-size": "1.25rem" }}>⚠</span>
            <span>{errorMessage()}</span>
          </div>
        </Show>

        <Form onSubmit={handleSubmit}>
          {/* File Upload Section */}
          <Section
            title="📁 Upload Files"
            description="Select your Pyxis inventory and usage Excel files"
          >
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
          </Section>

          {/* Filter Options Section */}
          <Section
            title="🔍 Filter Options"
            description="Configure which items to include in the report"
          >
            <CheckboxField
              name="onlyCritical"
              label="Only include critical items"
              description="Show only items below the critical threshold"
              Field={Field}
            />
            <CheckboxField
              name="includeUnordered"
              label="Include unordered items"
              description="Include items that haven't been ordered yet"
              Field={Field}
            />
            <CheckboxField
              name="includeMinZero"
              label="Include items with a min of 0"
              description="Include items with minimum quantity set to zero"
              Field={Field}
            />
          </Section>

          {/* Thresholds Section */}
          <Section
            title="⚙️ Threshold Settings"
            description="Set the criteria for critical items and projection period"
          >
            <NumberField
              name="criticalThreshold"
              label="Critical Threshold (days)"
              description="Number of days before stock runs out to flag as critical"
              Field={Field}
            />
            <NumberField
              name="maxDays"
              label="Maximum Days"
              description="Maximum number of days to project into the future"
              Field={Field}
            />
          </Section>

          {/* Device Selection Section */}
          <Section
            title="🏥 Device Selection"
            description="Specify which devices to include or exclude from the report"
          >
            <DynamicListField
              name="devices"
              label="Include Devices"
              placeholder="Device name (e.g., EMER, ICU, OR1)"
              description="Leave blank to include all devices"
              form={form}
              Field={Field}
              FieldArray={FieldArray}
            />
            <DynamicListField
              name="exclude"
              label="Exclude Devices"
              placeholder="Device name (e.g., STORAGE, ARCHIVE)"
              description="Devices to explicitly exclude from the report"
              form={form}
              Field={Field}
              FieldArray={FieldArray}
            />
          </Section>

          {/* Submit Button */}
          <div
            style={{
              padding: "1.5rem",
              background: "white",
              border: "1px solid #e2e8f0",
              "border-radius": "12px",
              "box-shadow": "0 1px 3px rgba(0, 0, 0, 0.05)",
            }}
          >
            <button
              type="submit"
              style={{
                padding: "1rem 2rem",
                background: isLoading() ? "#94a3b8" : "#3b82f6",
                color: "white",
                border: "none",
                "border-radius": "8px",
                cursor: isLoading() ? "not-allowed" : "pointer",
                "font-size": "1.125rem",
                "font-weight": "600",
                width: "100%",
                transition: "all 0.2s",
                "box-shadow": isLoading()
                  ? "none"
                  : "0 4px 6px rgba(59, 130, 246, 0.3)",
              }}
              disabled={isLoading()}
              onMouseEnter={(e) =>
                !isLoading() && (e.currentTarget.style.background = "#2563eb")
              }
              onMouseLeave={(e) =>
                !isLoading() && (e.currentTarget.style.background = "#3b82f6")
              }
            >
              {isLoading() ? (
                <div
                  style={{
                    display: "flex",
                    "align-items": "center",
                    "justify-content": "center",
                    gap: "0.75rem",
                  }}
                >
                  <div
                    style={{
                      width: "20px",
                      height: "20px",
                      border: "3px solid rgba(255, 255, 255, 0.3)",
                      "border-top-color": "white",
                      "border-radius": "50%",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span>{loadingStatus()}</span>
                </div>
              ) : (
                "Generate Report"
              )}
            </button>
          </div>
        </Form>

        {/* Footer */}
        <div
          style={{
            "margin-top": "2rem",
            "text-align": "center",
            color: "#94a3b8",
            "font-size": "0.875rem",
          }}
        >
          <p>Pyxis Inventory Report Generator v1.0</p>
        </div>
      </div>

      {/* Add CSS animation for spinner */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
