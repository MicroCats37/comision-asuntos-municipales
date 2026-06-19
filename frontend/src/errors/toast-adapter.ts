/**
 * Swappable toast adapter.
 * Core hooks call notify.error() / notify.success() without knowing
 * which toast library is behind. Projects configure it once in their provider.
 */

type ToastFn = (message: string) => void;

let _error: ToastFn = (msg) => console.error("[API Error]", msg);
let _success: ToastFn = (msg) => console.log("[API Success]", msg);

/**
 * Configure the toast implementation.
 * Call this once in your root provider (e.g., ReactQueryProvider).
 *
 * @example
 * import { toast } from "sonner";
 * configureToast(toast.error, toast.success);
 */
export function configureToast(error: ToastFn, success: ToastFn) {
  _error = error;
  _success = success;
}

export const notify = {
  error: (msg: string) => _error(msg),
  success: (msg: string) => _success(msg),
};
