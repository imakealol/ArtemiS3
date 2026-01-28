export type MeilisearchRefreshStatus = {
  status: "idle" | "running" | "done" | "error";
  processed: number;
  total: number;
  percent: number;
  started_at?: string;
  finished_at?: string;
  message?: string;
};
