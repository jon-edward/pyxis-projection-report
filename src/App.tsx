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
import "./styles.css";

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

// Cache key for localStorage
const CACHE_KEY = "pyxis_report_config_v1";

// Load cached configuration from localStorage
function loadCachedConfig() {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      return JSON.parse(cached);
    }
  } catch (error) {
    console.error("Error loading cached config:", error);
  }
  return null;
}

// Save configuration to localStorage
function saveCachedConfig(config: any) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(config));
  } catch (error) {
    console.error("Error saving cached config:", error);
  }
}

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
    <div class="checkbox-field">
      <Field name={name} type="boolean">
        {(field: any, inputProps: any) => (
          <div>
            <div class="checkbox-container">
              <input
                type="checkbox"
                id={id}
                class="checkbox-input"
                {...inputProps}
                checked={field.value}
              />
              <label for={id} class="checkbox-label">
                {label}
              </label>
            </div>
            {description && <p class="checkbox-description">{description}</p>}
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
    <div class="number-field">
      <Field name={name} type="number">
        {(field: any, inputProps: any) => (
          <div class="field-container">
            <label for={name} class="field-label">
              {label}
            </label>
            {description && <p class="field-description">{description}</p>}
            <input
              type="number"
              id={name}
              class="number-input"
              {...inputProps}
              value={field.value ?? 0}
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
    <div class="file-field">
      <Field name={name} type="file">
        {(field: any, inputProps: any) => (
          <div class="field-container">
            <label for={name} class="field-label">
              {label}
            </label>
            <input
              class="file-input"
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
            />
            <Show when={selectedFile()}>
              <div class="file-selected">
                ✓ Selected: {selectedFile()!.name} (
                {(selectedFile()!.size / 1024).toFixed(1)} KB)
              </div>
            </Show>
            {field.error && (
              <div class="field-error">
                <span>{props.errorMessage}</span>
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
    <div class="dynamic-list-field">
      <FieldArray name={name}>
        {(fieldArray: any) => (
          <div>
            <div class="list-header">
              <label class="field-label">{label}</label>
              {description && <p class="field-description">{description}</p>}
            </div>
            <For each={fieldArray.items.slice(0, -1)}>
              {(item: any, index: () => number) => (
                <Field name={`${name}.${index()}`}>
                  {(field: any, inputProps: any) => (
                    <div class="list-item">
                      <div class="list-item-row">
                        <input
                          {...inputProps}
                          value={field.value || ""}
                          placeholder={placeholder}
                          class={`list-input ${field.error ? "error" : ""}`}
                        />
                        <button
                          type="button"
                          class="btn-remove"
                          onClick={() => remove(form, name, { at: index() })}
                        >
                          Remove
                        </button>
                      </div>
                      {field.error && (
                        <div class="field-error">{field.error}</div>
                      )}
                    </div>
                  )}
                </Field>
              )}
            </For>

            <Field name={`${name}.${fieldArray.items.length - 1}`}>
              {(field: any, inputProps: any) => (
                <div class="list-item-last">
                  <input
                    {...inputProps}
                    value={field.value || ""}
                    placeholder={placeholder}
                    class={`list-input-last ${field.error ? "error" : ""}`}
                  />
                  {field.error && <div class="field-error">{field.error}</div>}
                </div>
              )}
            </Field>

            <button
              type="button"
              class="btn-add"
              onClick={() => insert(form, name, { value: "" })}
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
    <div class="section">
      <h3 class="section-title">{props.title}</h3>
      {props.description && (
        <p class="section-description">{props.description}</p>
      )}
      {props.children}
    </div>
  );
}

// Main App Component
export default function App() {
  const cachedConfig = loadCachedConfig();

  const [form, { Form, Field, FieldArray }] = createForm<ReportConfig>({
    validate: valiForm(ReportConfigSchema),
    initialValues: cachedConfig || {
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

    // Save configuration to cache (excluding files)
    const configToCache = {
      onlyCritical: result.onlyCritical,
      includeUnordered: result.includeUnordered,
      includeMinZero: result.includeMinZero,
      criticalThreshold: result.criticalThreshold,
      maxDays: result.maxDays,
      devices: result.devices,
      exclude: result.exclude,
    };
    saveCachedConfig(configToCache);

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
    <div class="app-container">
      <div class="app-content">
        {/* Header */}
        <div class="header">
          <div class="header-content">
            <div>
              <h1 class="header-title">Pyxis Inventory Report Generator</h1>
              <p class="header-subtitle">
                Configure and generate your inventory projection reports
              </p>
            </div>
            <Show when={cachedConfig}>
              <button
                type="button"
                class="btn-clear-cache"
                onClick={() => {
                  if (
                    confirm(
                      "Are you sure you want to clear all cached settings?"
                    )
                  ) {
                    localStorage.removeItem(CACHE_KEY);
                    window.location.reload();
                  }
                }}
              >
                Clear Cache
              </button>
            </Show>
          </div>
          <Show when={cachedConfig}>
            <div class="cache-indicator">
              ℹ️ Previous settings loaded from cache
            </div>
          </Show>
        </div>

        {/* Success Message */}
        <Show when={successMessage()}>
          <div class="message message-success">
            <span class="message-icon">✓</span>
            <span>{successMessage()}</span>
          </div>
        </Show>

        {/* Error Message */}
        <Show when={errorMessage()}>
          <div class="message message-error">
            <span class="message-icon">⚠</span>
            <span>{errorMessage()}</span>
          </div>
        </Show>

        <Form onSubmit={handleSubmit}>
          {/* File Upload Section */}
          <Section
            title="Upload Files"
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
            title="Filter Options"
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
            title="Threshold Settings"
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
            title="Device Selection"
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
          <div class="submit-container">
            <button
              type="submit"
              class={`btn-submit ${isLoading() ? "loading" : ""}`}
              disabled={isLoading()}
            >
              {isLoading() ? (
                <div class="loading-content">
                  <div class="spinner" />
                  <span>{loadingStatus()}</span>
                </div>
              ) : (
                "Generate Report"
              )}
            </button>
          </div>
        </Form>

        {/* Footer */}
        <div class="footer">
          <p>Pyxis Inventory Report Generator v1.0</p>
        </div>
      </div>
    </div>
  );
}
