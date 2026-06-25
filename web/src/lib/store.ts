import { openDB, type IDBPDatabase } from "idb";
import type { RunRecord } from "./schemas";

const DB_NAME = "hiring-agent";
const DB_VERSION = 1;
const STORE = "runs";
const INDEX = "by-createdAt";

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDB(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE)) {
          const store = db.createObjectStore(STORE, { keyPath: "id" });
          store.createIndex(INDEX, "createdAt");
        }
      },
    });
  }
  return dbPromise;
}

export async function saveRun(rec: RunRecord): Promise<void> {
  const db = await getDB();
  await db.put(STORE, rec);
}

export async function listRuns(): Promise<RunRecord[]> {
  const db = await getDB();
  return (await db.getAllFromIndex(STORE, INDEX)) as RunRecord[];
}

export async function getRun(id: string): Promise<RunRecord | undefined> {
  const db = await getDB();
  return (await db.get(STORE, id)) as RunRecord | undefined;
}

export async function deleteRun(id: string): Promise<void> {
  const db = await getDB();
  await db.delete(STORE, id);
}

export async function renameRun(id: string, label: string): Promise<void> {
  const db = await getDB();
  const rec = (await db.get(STORE, id)) as RunRecord | undefined;
  if (!rec) return;
  rec.label = label;
  await db.put(STORE, rec);
}

export async function clearAllRuns(): Promise<void> {
  const db = await getDB();
  await db.clear(STORE);
}
