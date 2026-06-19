import { v4 as uuidv4 } from "uuid";

/**
 * Robust boolean parser for environment variables.
 * Handles strings like 'true', '1', 'on', 'yes'.
 */
const toBoolean = (val: string | undefined): boolean => {
  if (!val) return false;
  const s = val.trim().toLowerCase();
  return s === "true" || s === "1" || s === "on" || s === "yes";
};

/**
 * Manual UUID generator fallback for non-secure contexts (HTTP)
 * where the native crypto or library might have issues.
 */
const manualGenerateUUID = (): string => {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

/**
 * Decides which UUID generator to use.
 * Priority:
 * 1. Force manual generation if NEXT_PUBLIC_IS_TEST_UUID is truthy.
 * 2. Fallback to manual if in a non-secure context (HTTP) in the browser.
 * 3. Default to standard uuid library.
 */
const getUUID = (): string => {
  const isTestMode = toBoolean(process.env.NEXT_PUBLIC_IS_TEST_UUID);
  const isNotSecure =
    typeof window !== "undefined" && window.isSecureContext === false;

  if (isTestMode || isNotSecure) {
    return manualGenerateUUID();
  }

  try {
    return uuidv4();
  } catch (error) {
    console.warn("[PayloadBuilder] v4 library failed, falling back", error);
    return manualGenerateUUID();
  }
};

const FILE_PREFIX = "file_";

export type PayloadResult<T> = FormData | T;

/**
 * Automatically detects File objects in the payload and converts to FormData.
 * If no files are found, returns the original object (sent as JSON by Axios).
 */
export function buildApiPayload<T>(inputData: T): PayloadResult<T> {
  const fileList: Array<{ token: string; file: File }> = [];

  const scanAndTokenize = (node: unknown): unknown => {
    if (node === null || node === undefined) return node;

    if (node instanceof File) {
      const uuid = getUUID();
      const token = `${FILE_PREFIX}${uuid}`;
      fileList.push({ token, file: node });
      return token;
    }

    if (node instanceof Date) return node;
    if (Array.isArray(node)) return node.map(scanAndTokenize);

    if (typeof node === "object") {
      const result: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(
        node as Record<string, unknown>,
      )) {
        result[key] = scanAndTokenize(value);
      }
      return result;
    }

    return node;
  };

  const tokenizedData = scanAndTokenize(inputData);

  if (fileList.length === 0) return inputData;

  const formData = new FormData();
  formData.append("data", JSON.stringify(tokenizedData));

  // The backend uses token___realname to identify the link in the JSON payload natively
  // without losing the original file name formatting.
  for (const item of fileList) {
    const overloadedName = `${item.token}___${item.file.name}`;
    formData.append("files", item.file, overloadedName);
  }

  return formData;
}
