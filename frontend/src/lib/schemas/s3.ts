export type S3ObjectModel = {
  key: string;
  size: number;
  lastModified?: string;
  storageClass?: string;
  tags?: string[];
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
  sortBy?: "Key" | "Size" | "LastModified";
  sortDirection?: "asc" | "desc";
};

export type S3FolderModel = {
  path: string;
  name: string;
  depth: number;
  matched_count: number;
};

export type S3BreadcrumbModel = {
  path: string;
  name: string;
};

export type S3FolderChildrenResponse = {
  path: string;
  breadcrumbs: S3BreadcrumbModel[];
  children: S3FolderModel[];
  files?: S3ObjectModel[];
};

export type S3FolderSearchRequest = {
  s3Uri: string;
  contains?: string;
  limit?: number;
};

export type S3FolderChildrenRequest = {
  s3Uri: string;
  path?: string;
  contains?: string;
  limit?: number;
  sortBy?: "Key" | "Size" | "LastModified";
  sortDirection?: "asc" | "desc";
};
