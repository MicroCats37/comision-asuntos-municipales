import { describe, expect, it } from "vitest";
import { createLatestRequestGuard } from "./useLatestRequestGuard";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("latest request guard", () => {
  it("prevents an older response from committing after a newer response", async () => {
    const guard = createLatestRequestGuard();
    const older = deferred<string>();
    const newer = deferred<string>();
    const committed: string[] = [];

    const commit = async (requestId: number, request: Promise<string>) => {
      const value = await request;
      if (guard.isLatest(requestId)) committed.push(value);
    };

    const olderTask = commit(guard.begin(), older.promise);
    const newerTask = commit(guard.begin(), newer.promise);

    newer.resolve("newer");
    await newerTask;
    older.resolve("older");
    await olderTask;

    expect(committed).toEqual(["newer"]);
  });
});
