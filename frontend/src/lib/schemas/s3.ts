export type S3ObjectModel = {
  key: string;
  size: number;
  last_modified?: string;
  storage_class?: string;
};

export type S3SearchRequest = {
  s3Uri: string;
  contains?: string;
  limit?: number;
  suffixes?: string[];
  minSize?: number;
  maxSize?: number;
  storageClasses?: string[];
  modifiedAfter?: string;
  modifiedBefore?: string;
  sort_by?: "Key" | "Size" | "LastModified";
  sort_direction?: "asc" | "desc";
};
